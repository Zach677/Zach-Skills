from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".aiff", ".alac", ".ogg", ".wma", ".opus"}


def audio_files(root: Path) -> list[Path]:
    if not root.is_dir():
        raise ValueError(f"source folder does not exist or is not a directory: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)
    if not files:
        raise ValueError(f"source folder contains no supported audio files: {root}")
    return files
