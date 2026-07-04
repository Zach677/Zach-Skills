#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".aiff", ".alac", ".ogg", ".wma", ".opus"}


def ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-print_format",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "ffprobe failed"}
    return json.loads(result.stdout or "{}")


def normalized_tags(metadata: dict) -> dict[str, str]:
    tags = metadata.get("format", {}).get("tags") or {}
    return {str(key).lower(): str(value).strip() for key, value in tags.items()}


def has_cover(metadata: dict) -> bool:
    for stream in metadata.get("streams") or []:
        if (stream.get("disposition") or {}).get("attached_pic") == 1:
            return True
    return False


def catalog_comment(tags: dict[str, str]) -> tuple[bool, str]:
    raw = tags.get("comment") or tags.get("cmt")
    if not raw:
        return False, "missing"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return False, "not_json"
    track_id = str(payload.get("trackID", ""))
    album_id = str(payload.get("albumID", ""))
    if not track_id.isdigit() or not album_id.isdigit():
        return False, "ids_not_numeric"
    return True, "ok"


def scan(root: Path) -> list[dict[str, object]]:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)
    rows = []
    for path in files:
        metadata = ffprobe(path)
        tags = normalized_tags(metadata)
        catalog_ok, catalog_reason = catalog_comment(tags)
        rows.append(
            {
                "path": path,
                "title": bool(tags.get("title")),
                "artist": bool(tags.get("artist")),
                "album": bool(tags.get("album")),
                "album_artist": bool(tags.get("album_artist") or tags.get("albumartist")),
                "lyrics": bool(tags.get("lyrics") or tags.get("lyr")),
                "cover": has_cover(metadata),
                "catalog_comment": catalog_ok,
                "catalog_reason": catalog_reason,
                "error": metadata.get("error"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether audio files are ready for MuseAmp direct import.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    if not shutil.which("ffprobe"):
        raise SystemExit("ffprobe not found")

    rows = scan(args.root)
    print(f"files={len(rows)}")

    keys = ["title", "artist", "album", "album_artist", "lyrics", "cover", "catalog_comment"]
    for key in keys:
        print(f"{key}_ok={sum(1 for row in rows if row[key])}/{len(rows)}")

    broken = [
        row for row in rows
        if row["error"] or any(not row[key] for key in keys)
    ]
    print(f"not_museamp_ready={len(broken)}/{len(rows)}")
    print()

    for row in broken:
        missing = [key for key in keys if not row[key]]
        detail = row["error"] or ",".join(missing)
        if "catalog_comment" in missing:
            detail += f" ({row['catalog_reason']})"
        print(f"{row['path']}\t{detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
