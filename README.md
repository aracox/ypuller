# ypuller

`ypuller` is a local command-line agent that takes an artist name, reads the artist's
official studio-album catalog from MusicBrainz, searches YouTube for each track, and saves
confident matches as audio-only `.m4a` files grouped by album.

If MusicBrainz is temporarily unavailable, ypuller falls back to Deezer's public catalog and
filters obvious compilations, live albums, remixes, and anniversary collections by title.

Use it only for media you own, have permission to download, or may download under applicable
law. The program does not bypass private, paid, members-only, geographic, authentication, or
DRM restrictions.

## Output

```text
downloads/
└── Artist/
    ├── .ypuller-manifest.json
    └── Album/
        ├── 01 - First Song.m4a
        └── 02 - Second Song.m4a
```

Each file contains audio only and receives title, artist, album, track-number, and release-year
metadata. The manifest prevents completed tracks from being downloaded again.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- FFmpeg and ffprobe on `PATH`
- Node.js 22 or newer on `PATH` for yt-dlp's YouTube challenge solver

On macOS with Homebrew, install FFmpeg with:

```sh
brew install ffmpeg node
```

## Setup

Install the application and its locked dependencies:

```sh
uv sync
```

No YouTube API key is required. Optionally create a local configuration file to identify this
application to MusicBrainz:

```sh
cp .env.example .env
```

`YPULLER_CONTACT` identifies this application to MusicBrainz and should be your email address
or website. The command works without it, using a generic local-use identifier.

The application deliberately does not parse `.env` files. Export the values into the current
shell before running it:

```sh
set -a
source .env
set +a
```

## Run

Pass one artist name:

```sh
uv run ypuller bodyslam
```

For an artist name containing spaces:

```sh
uv run ypuller "artist name"
```

Choose another output directory with:

```sh
uv run ypuller bodyslam --output /path/to/music
```

The input is interpreted as an artist, not a song or album. Exact MusicBrainz artist matches
are accepted automatically; ambiguous names stop without downloading. Only primary albums are
included. Singles, EPs, compilations, live albums, remixes, and other secondary album types are
excluded.

For each track, yt-dlp searches public YouTube results without an API key. ypuller compares title,
artist/channel, official-channel indicators, and duration. It skips a track when the leading
result is weak or too close to another candidate. A skip is safer than silently downloading the
wrong recording.

## Development

Python module filenames use `snake_case`, following Python conventions; user-facing paths and
directories otherwise follow the repository's naming guidance.

Install development dependencies:

```sh
uv sync --extra dev
```

Run the canonical checks:

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
```

Tests mock MusicBrainz, YouTube, yt-dlp, and FFmpeg interactions, so the normal test suite makes
no network requests and downloads no media.

## Limitations

- MusicBrainz data can be incomplete or contain multiple regional editions.
- Unauthenticated YouTube page search can break when YouTube changes its internal behavior and
  does not guarantee that a recording is downloadable.
- Website changes may require updating `yt-dlp` with `uv sync --upgrade-package yt-dlp`.
- A skipped match requires better catalog/search metadata; ypuller does not offer an unsafe
  "download the first result" fallback.
