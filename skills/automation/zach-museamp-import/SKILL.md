---
name: zach-museamp-import
description: >
  Use when Zach wants to prepare newly downloaded local music for MuseAmp import, especially after downloading songs/albums and asking to plan, validate, flatten, or create a MuseAmpReady folder. Converts a tagged source folder into MuseAmp-compatible copies with numeric catalog metadata and validates before Zach imports.
metadata:
  author: zach
  version: "0.1.0"
---

# zach-museamp-import

Prepare local audio folders for MuseAmp's local-library-first importer. This skill inspects a source music folder, creates non-destructive MuseAmp-ready copies, adds the catalog-style comment metadata MuseAmp expects, and hands Zach a flat folder whose files can be selected in MuseAmp's import picker.

## When to use

Use this skill when Zach:

- downloads new local music and wants it planned or prepared for MuseAmp import;
- asks whether a folder is MuseAmp-compatible;
- asks for a `MuseAmpReady-*` folder, a flat import folder, or a validation pass before manual import;
- wants local direct import instead of running Subsonic/Gonic/Navidrome for MuseAmp.

Do not use this skill to download music, bypass DRM, mutate the source folder, operate on cloud libraries, or import into MuseAmp without Zach explicitly asking for app automation.

## Inputs

- Required: a source folder containing local audio files.
- Optional: an output folder. Default to `/Users/star/Downloads/MuseAmpReady-<timestamp>-<source-name>`.
- Required tools: Python 3, `ffprobe`, and `ffmpeg`.

## Files Provided

- `scripts/check_museamp_ready.py`: scans audio files and reports standard tags, embedded cover art, lyrics, and MuseAmp catalog comment readiness.
- `scripts/make_museamp_ready_copy.py`: creates copied audio files with numeric `trackID` and `albumID` comment JSON. Pass `--flat` unless Zach asks for a structured output.

## Workflow

```text
[1] Confirm source folder and tool availability.
[2] Run the readiness check on the source folder.
[3] Create a flat MuseAmpReady output folder without touching originals.
[4] Run the readiness check on the output folder.
[5] Give Zach the exact output folder and import instruction.
```

### 1. Confirm Input

Resolve the source path from Zach's message. If no path is provided and the current conversation does not clearly identify one, ask for the folder path.

Before processing, confirm the basic toolchain:

```bash
command -v python3
command -v ffprobe
command -v ffmpeg
```

If `ffprobe` or `ffmpeg` is missing, stop and tell Zach that FFmpeg is required before the skill can prepare files.

### 2. Check Source Folder

Run:

```bash
SKILL_DIR="<path-to-this-skill>"
SRC="<source-folder>"
python3 "$SKILL_DIR/scripts/check_museamp_ready.py" "$SRC"
```

Interpretation:

- `title`, `artist`, `album`, `album_artist`, `cover`, and `lyrics` describe ordinary listening metadata.
- `catalog_comment` is the MuseAmp-specific compatibility marker.
- Standard tags alone are not enough for direct MuseAmp import. MuseAmp expects an iTunes-style comment JSON with numeric `trackID` and `albumID`.

Continue even if the source fails `catalog_comment`; the copy step is designed to fix that. Stop if there are zero audio files, unreadable media, DRM-protected files, or missing core tags that Zach needs to repair at the source.
The checker exits non-zero whenever the folder is not ready; a source folder
missing only `catalog_comment` is the expected pre-conversion case.

### 3. Create MuseAmpReady Copies

Prefer a flat output folder because MuseAmp's picker may allow selecting songs but not a parent folder.

Run:

```bash
SKILL_DIR="<path-to-this-skill>"
SRC="<source-folder>"
OUT="/Users/star/Downloads/MuseAmpReady-$(date +%Y%m%d-%H%M%S)-$(basename "$SRC")"
python3 "$SKILL_DIR/scripts/make_museamp_ready_copy.py" --flat "$SRC" "$OUT"
```

Rules:

- Never write into `SRC`.
- Never overwrite a non-empty `OUT`.
- Preserve original audio streams and metadata with stream copy.
- Use deterministic numeric IDs generated from the source-relative path.

### 4. Validate Output

Run:

```bash
python3 "$SKILL_DIR/scripts/check_museamp_ready.py" "$OUT"
```

Success contract:

- `catalog_comment_ok=N/N`
- `not_museamp_ready=0/N`
- the file count equals the expected number of source audio files.

If lyrics are absent, report that as a source metadata issue. Do not promise that Gonic/Subsonic lyrics will appear in MuseAmp's local playback view.

### 5. Handoff To Zach

Tell Zach to import the generated flat folder's audio files into MuseAmp, not the original source folder. If the picker only accepts files, open the flat folder, select all generated files, and import them.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Editing original downloads in place | Always create a separate `MuseAmpReady-*` output folder. |
| Importing the source folder directly | Import the generated flat output files instead. |
| Assuming folders define MuseAmp library structure | MuseAmp reads embedded metadata; folder layout is only a source-library convenience. |
| Leaving ordinary text in the comment tag | The copy step must write JSON with numeric `trackID` and `albumID`. |
| Generating nested output for normal MuseAmp import | Use `--flat` unless Zach explicitly wants a structured archive. |
| Treating Subsonic/Gonic as required | For direct MuseAmp import, a local ready folder is simpler and more reliable. |
| Expecting missing lyrics to be fixed by MuseAmp | Lyrics should be embedded in the local file before import. |
| Processing DRM or streaming-cache files | Stop and ask Zach for DRM-free local audio files. |

## Verification

- [ ] `python3 scripts/check_museamp_ready.py "<source-folder>"` ran.
- [ ] `python3 scripts/make_museamp_ready_copy.py --flat "<source-folder>" "<output-folder>"` ran.
- [ ] `python3 scripts/check_museamp_ready.py "<output-folder>"` reports `catalog_comment_ok=N/N`.
- [ ] `python3 scripts/check_museamp_ready.py "<output-folder>"` reports `not_museamp_ready=0/N`.
- [ ] Final response names the output folder and says it is the folder Zach should use for MuseAmp import.
