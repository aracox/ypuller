#!/usr/bin/env python3
"""List every song with artist in the format [artist,song] from the downloads folder.

Saves the unique list of songs to downloads/song.txt.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".flac", ".wav", ".aac", ".ogg", ".opus"}


def extract_songs(download_dir: Path) -> list[tuple[str, str]]:
    """Scan download directory and return sorted unique (artist, song) tuples."""
    unique_songs: set[tuple[str, str]] = set()

    for path in download_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        rel_path = path.relative_to(download_dir)
        if len(rel_path.parts) < 2:
            continue

        artist = rel_path.parts[0]
        stem = path.stem
        match = re.match(r"^\d+\s*-\s*(.+)$", stem)
        song = match.group(1).strip() if match else stem.strip()

        if artist and song:
            unique_songs.add((artist, song))

    return sorted(unique_songs, key=lambda item: (item[0].casefold(), item[1].casefold()))


def write_song_list(songs: list[tuple[str, str]], output_file: Path) -> None:
    """Write [artist,song] lines to output file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"[{artist},{song}]\n" for artist, song in songs)
    output_file.write_text(content, encoding="utf-8")


def resolve_default_download_dir() -> Path:
    """Resolve default downloads directory based on cwd or repository root."""
    cwd_downloads = Path("downloads")
    if cwd_downloads.is_dir():
        return cwd_downloads.resolve()

    repo_downloads = Path(__file__).resolve().parent.parent / "downloads"
    if repo_downloads.is_dir():
        return repo_downloads

    return cwd_downloads.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List all downloaded songs with their artist and save to song.txt."
    )
    parser.add_argument(
        "download_dir",
        nargs="?",
        type=Path,
        default=None,
        help="Path to downloads directory (default: downloads/)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path to output file (default: <download_dir>/song.txt)",
    )

    args = parser.parse_args(argv)

    download_dir = args.download_dir
    if download_dir is None:
        download_dir = resolve_default_download_dir()
    else:
        download_dir = download_dir.resolve()

    if not download_dir.is_dir():
        print(f"Error: Download directory not found: {download_dir}", file=sys.stderr)
        return 1

    output_file = (
        download_dir / "song.txt" if args.output is None else args.output.resolve()
    )

    songs = extract_songs(download_dir)
    write_song_list(songs, output_file)

    artist_count = len({artist for artist, _ in songs})
    print(f"Found {len(songs)} unique songs across {artist_count} artists.")
    print(f"Saved to {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
