import json
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ypuller.models import Album, Artist, Track


class CatalogError(RuntimeError):
    pass


class MusicBrainzClient:
    base_url = "https://musicbrainz.org/ws/2"

    def __init__(self, contact: str, min_interval: float = 1.1):
        self.user_agent = f"ypuller/0.1 ({contact})"
        self.min_interval = min_interval
        self._last_request = 0.0

    def _get(self, path: str, params: dict[str, object]) -> dict:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)

        url = f"{self.base_url}/{path}?{urlencode(params)}"
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": self.user_agent},
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise CatalogError(f"MusicBrainz request failed with HTTP {error.code}") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise CatalogError("MusicBrainz request failed") from error
        finally:
            self._last_request = time.monotonic()
        return payload

    def resolve_artist(self, keyword: str) -> Artist:
        data = self._get(
            "artist/",
            {"query": f'artist:"{keyword}"', "fmt": "json", "limit": 5},
        )
        artists = data.get("artists", [])
        if not artists:
            raise CatalogError(f'No MusicBrainz artist found for "{keyword}"')

        normalized_keyword = _normalize_name(keyword)
        exact = [
            artist
            for artist in artists
            if _normalize_name(artist.get("name", "")) == normalized_keyword
        ]
        if len(exact) == 1:
            selected = exact[0]
        elif len(exact) > 1:
            names = ", ".join(_artist_label(artist) for artist in exact)
            raise CatalogError(f'Ambiguous artist "{keyword}": {names}')
        else:
            ranked = sorted(artists, key=_score, reverse=True)
            top_score = _score(ranked[0])
            second_score = _score(ranked[1]) if len(ranked) > 1 else 0
            if top_score < 95 or top_score - second_score < 10:
                names = ", ".join(_artist_label(artist) for artist in ranked[:3])
                raise CatalogError(f'Artist "{keyword}" is not an exact match. Candidates: {names}')
            selected = ranked[0]

        return Artist(id=selected["id"], name=selected["name"])

    def get_albums(self, artist_id: str) -> list[Album]:
        groups = self._get(
            "release-group/",
            {"artist": artist_id, "type": "album", "fmt": "json", "limit": 100},
        ).get("release-groups", [])
        primary_albums = [
            group
            for group in groups
            if group.get("primary-type") == "Album" and not group.get("secondary-types", [])
        ]
        primary_albums.sort(key=lambda group: group.get("first-release-date") or "9999")

        albums = []
        for group in primary_albums:
            album = self._get_album(group)
            if album is not None:
                albums.append(album)
        return albums

    def _get_album(self, group: dict) -> Album | None:
        data = self._get(
            "release/",
            {
                "release-group": group["id"],
                "status": "official",
                "inc": "recordings+media",
                "fmt": "json",
                "limit": 100,
            },
        )
        releases = [
            release
            for release in data.get("releases", [])
            if release.get("status", "").casefold() == "official" and release.get("media")
        ]
        releases.sort(key=lambda release: release.get("date") or "9999")

        for release in releases:
            tracks = _tracks_from_release(release)
            if tracks:
                date = group.get("first-release-date") or release.get("date") or ""
                return Album(
                    id=group["id"],
                    title=group["title"],
                    year=date[:4],
                    tracks=tracks,
                )
        return None


def _tracks_from_release(release: dict) -> list[Track]:
    tracks = []
    for medium in release.get("media", []):
        for raw_track in medium.get("tracks", []):
            recording = raw_track.get("recording", {})
            title = raw_track.get("title") or recording.get("title")
            if not title:
                continue
            duration_ms = raw_track.get("length") or recording.get("length")
            duration = round(int(duration_ms) / 1000) if duration_ms else None
            number = len(tracks) + 1
            track_id = recording.get("id") or raw_track.get("id") or f"track-{number}"
            tracks.append(Track(track_id, title, number, duration))
    return tracks


def _normalize_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _score(artist: dict) -> int:
    try:
        return int(artist.get("score", 0))
    except (TypeError, ValueError):
        return 0


def _artist_label(artist: dict) -> str:
    label = artist.get("name", "unknown")
    if artist.get("disambiguation"):
        label += f" ({artist['disambiguation']})"
    return label
