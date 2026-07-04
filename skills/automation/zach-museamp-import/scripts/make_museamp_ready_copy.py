#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import zlib
from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".aiff", ".alac", ".ogg", ".wma", ".opus"}


def numeric_id(prefix: int, value: str) -> str:
    return str(prefix + (zlib.crc32(value.encode("utf-8")) % 900_000_000))


def audio_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)


def clean_filename(value: str) -> str:
    return re.sub(r'[/:]', " - ", value).strip()


def output_path(source_root: Path, output_root: Path, source: Path, flat: bool) -> Path:
    relative = source.relative_to(source_root)
    if not flat:
        return output_root / relative

    album = relative.parts[0] if len(relative.parts) > 1 else "Unknown Album"
    target = output_root / clean_filename(f"{album} - {source.name}")
    index = 2
    while target.exists():
        target = output_root / clean_filename(f"{album} - {source.stem} ({index}){source.suffix}")
        index += 1
    return target


def convert(source_root: Path, output_root: Path, flat: bool) -> int:
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output exists and is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for source in audio_files(source_root):
        relative = source.relative_to(source_root)
        destination = output_path(source_root, output_root, source, flat)
        destination.parent.mkdir(parents=True, exist_ok=True)

        album_key = str(relative.parent)
        track_key = str(relative)
        payload = {
            "v": 1,
            "trackID": numeric_id(100_000_000, track_key),
            "albumID": numeric_id(200_000_000, album_key),
        }

        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-map",
                "0",
                "-c",
                "copy",
                "-map_metadata",
                "0",
                "-metadata",
                f"comment={json.dumps(payload, separators=(',', ':'))}",
                str(destination),
            ],
            check=True,
        )
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Create MuseAmp-ready audio copies without changing originals.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--flat", action="store_true", help="Put all generated files in one directory.")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found")

    count = convert(args.source, args.output, args.flat)
    print(f"copied={count}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
