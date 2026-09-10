from pathlib import Path

import ypuller.cli as cli
from ypuller.catalog import CatalogUnavailable
from ypuller.cli import download_artist
from ypuller.models import Album, Artist, Candidate, Track


class FakeCatalog:
    def resolve_artist(self, keyword):
        return Artist("artist-1", "Bodyslam")

    def get_albums(self, artist_id):
        track = Track("recording-1", "Life", 1, 241)
        return [Album("album-1", "Believe", "2005", [track])]


class FakeYouTube:
    def __init__(self):
        self.search_count = 0

    def search(self, artist, track):
        self.search_count += 1
        return [Candidate("video-1", "Bodyslam - Life Official Audio", "Bodyslam", 241)]


class FakeMedia:
    def download(self, artist, album, track, candidate, output_dir):
        path = Path(output_dir) / artist / album.title / "01 - Life.m4a"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return path


def test_downloads_once_then_uses_manifest_on_the_next_run(tmp_path):
    youtube = FakeYouTube()
    messages = []

    first_exit = download_artist(
        "bodyslam", tmp_path, FakeCatalog(), youtube, FakeMedia(), messages.append
    )
    second_exit = download_artist(
        "bodyslam", tmp_path, FakeCatalog(), youtube, FakeMedia(), messages.append
    )

    assert first_exit == 0
    assert second_exit == 0
    assert youtube.search_count == 1
    assert (tmp_path / "Bodyslam" / ".ypuller-manifest.json").is_file()
    assert any("downloaded=1" in message for message in messages)
    assert any("existing=1" in message for message in messages)


def test_main_does_not_require_a_youtube_api_key(monkeypatch, tmp_path):
    created = {}
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setattr(cli, "ensure_dependencies", lambda: None)
    monkeypatch.setattr(cli, "MusicBrainzClient", lambda contact: "catalog")
    monkeypatch.setattr(cli, "MediaDownloader", lambda: "media")

    def create_youtube():
        created["youtube"] = True
        return "youtube"

    monkeypatch.setattr(cli, "YouTubeClient", create_youtube)
    monkeypatch.setattr(cli, "download_artist", lambda *args: 0)

    assert cli.main(["bodyslam", "--output", str(tmp_path)]) == 0
    assert created["youtube"] is True


def test_main_uses_deezer_when_musicbrainz_is_unavailable(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "ensure_dependencies", lambda: None)
    monkeypatch.setattr(cli, "MusicBrainzClient", lambda contact: "musicbrainz")
    monkeypatch.setattr(cli, "DeezerClient", lambda: "deezer")
    monkeypatch.setattr(cli, "YouTubeClient", lambda: "youtube")
    monkeypatch.setattr(cli, "MediaDownloader", lambda: "media")

    def fake_download(keyword, output, catalog, youtube, media):
        calls.append(catalog)
        if catalog == "musicbrainz":
            raise CatalogUnavailable("unavailable")
        return 0

    monkeypatch.setattr(cli, "download_artist", fake_download)

    assert cli.main(["bodyslam", "--output", str(tmp_path)]) == 0
    assert calls == ["musicbrainz", "deezer"]
