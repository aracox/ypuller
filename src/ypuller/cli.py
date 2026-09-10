import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from ypuller.catalog import CatalogError, CatalogUnavailable, DeezerClient, MusicBrainzClient
from ypuller.matcher import select_candidate
from ypuller.media import MediaDownloader, MediaError, ensure_dependencies, safe_component
from ypuller.youtube import YouTubeClient, YouTubeError


class Manifest:
    def __init__(self, path: Path, output_root: Path):
        self.path = path
        self.output_root = output_root
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "tracks": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise MediaError(f"Cannot read manifest: {self.path}") from error
        if data.get("version") != 1 or not isinstance(data.get("tracks"), dict):
            raise MediaError(f"Unsupported manifest format: {self.path}")
        return data

    def has_file(self, track_id: str) -> bool:
        record = self.data["tracks"].get(track_id)
        if not record or not isinstance(record.get("path"), str):
            return False
        root = self.output_root.resolve()
        path = (root / record["path"]).resolve()
        return path.is_relative_to(root) and path.is_file()

    def mark_downloaded(self, track_id: str, video_id: str, path: Path) -> None:
        relative_path = path.resolve().relative_to(self.output_root.resolve())
        self.data["tracks"][track_id] = {
            "video_id": video_id,
            "path": str(relative_path),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


def download_artist(
    keyword: str,
    output_dir: Path,
    catalog,
    youtube,
    media,
    output: Callable[[str], None] = print,
) -> int:
    artist = catalog.resolve_artist(keyword)
    albums = catalog.get_albums(artist.id)
    if not albums:
        raise CatalogError(f'No official primary albums found for "{artist.name}"')

    track_count = sum(len(album.tracks) for album in albums)
    output(f'Resolved "{keyword}" to {artist.name}: {len(albums)} albums, {track_count} tracks')

    artist_dir = output_dir / safe_component(artist.name)
    manifest = Manifest(artist_dir / ".ypuller-manifest.json", output_dir)
    downloaded = existing = skipped = failed = 0

    for album in albums:
        output(f"Album: {album.title} ({album.year or 'unknown year'})")
        for track in album.tracks:
            manifest_key = f"{album.id}:{track.id}:{track.number}"
            if manifest.has_file(manifest_key):
                existing += 1
                continue

            candidates = youtube.search(artist.name, track.title)
            selected = select_candidate(artist.name, track, candidates)
            if selected is None:
                skipped += 1
                output(f"  skipped: {track.number:02d} - {track.title} (no confident match)")
                continue

            try:
                path = media.download(artist.name, album, track, selected, output_dir)
            except MediaError as error:
                failed += 1
                output(f"  failed: {track.number:02d} - {track.title}: {error}")
                continue

            manifest.mark_downloaded(manifest_key, selected.video_id, path)
            downloaded += 1
            output(f"  downloaded: {path}")

    output(
        f"Summary: downloaded={downloaded}, existing={existing}, skipped={skipped}, failed={failed}"
    )
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ypuller",
        description="Download authorized YouTube music by artist and organize it by album.",
        epilog="Only download media you own or have permission to download.",
    )
    parser.add_argument("artist", help="artist name, for example: bodyslam")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("downloads"),
        help="output directory (default: downloads)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ensure_dependencies()
        catalog = MusicBrainzClient(os.environ.get("YPULLER_CONTACT", "local-use@example.invalid"))
        youtube = YouTubeClient()
        media = MediaDownloader()
        try:
            return download_artist(args.artist, args.output, catalog, youtube, media)
        except CatalogUnavailable as error:
            print(f"warning: {error}; using Deezer catalog fallback", file=sys.stderr)
            return download_artist(args.artist, args.output, DeezerClient(), youtube, media)
    except (CatalogError, YouTubeError, MediaError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())
