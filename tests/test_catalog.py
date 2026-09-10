from ypuller.catalog import DeezerClient, MusicBrainzClient


class FakeMusicBrainzClient(MusicBrainzClient):
    def __init__(self, responses):
        super().__init__(contact="tests@example.com", min_interval=0)
        self.responses = iter(responses)

    def _get(self, path, params):
        return next(self.responses)


def test_resolves_an_exact_artist_name():
    client = FakeMusicBrainzClient(
        [
            {
                "artists": [
                    {"id": "other", "name": "Body Slam", "score": 80},
                    {"id": "artist-1", "name": "Bodyslam", "score": 100},
                ]
            }
        ]
    )

    artist = client.resolve_artist("bodyslam")

    assert artist.id == "artist-1"
    assert artist.name == "Bodyslam"


def test_builds_ordered_tracks_from_official_primary_albums():
    client = FakeMusicBrainzClient(
        [
            {
                "release-groups": [
                    {
                        "id": "live",
                        "title": "Live",
                        "primary-type": "Album",
                        "secondary-types": ["Live"],
                        "first-release-date": "2004-01-01",
                    },
                    {
                        "id": "album-1",
                        "title": "Believe",
                        "primary-type": "Album",
                        "secondary-types": [],
                        "first-release-date": "2005-04-01",
                    },
                ]
            },
            {
                "releases": [
                    {
                        "id": "release-1",
                        "status": "Official",
                        "date": "2005-04-01",
                        "media": [
                            {
                                "tracks": [
                                    {
                                        "id": "track-1",
                                        "position": 1,
                                        "title": "Life",
                                        "length": 241000,
                                        "recording": {"id": "recording-1", "title": "Life"},
                                    },
                                    {
                                        "id": "track-2",
                                        "position": 2,
                                        "title": "ความเชื่อ",
                                        "recording": {
                                            "id": "recording-2",
                                            "title": "ความเชื่อ",
                                            "length": 285000,
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ]
            },
        ]
    )

    albums = client.get_albums("artist-1")

    assert [album.title for album in albums] == ["Believe"]
    assert [track.title for track in albums[0].tracks] == ["Life", "ความเชื่อ"]
    assert [track.number for track in albums[0].tracks] == [1, 2]
    assert albums[0].tracks[1].duration_seconds == 285


class FakeDeezerClient(DeezerClient):
    def __init__(self, responses):
        self.responses = iter(responses)

    def _get(self, path, params):
        return next(self.responses)


def test_deezer_fallback_selects_the_popular_exact_artist_and_studio_albums():
    client = FakeDeezerClient(
        [
            {
                "data": [
                    {"id": 1, "name": "Bodyslam", "nb_fan": 0},
                    {"id": 254379, "name": "Bodyslam", "nb_fan": 205618},
                ]
            },
            {
                "data": [
                    {
                        "id": 10,
                        "title": "Believe",
                        "record_type": "album",
                        "release_date": "2005-04-22",
                    },
                    {
                        "id": 11,
                        "title": "Bodyslam Remix",
                        "record_type": "album",
                        "release_date": "2015-07-27",
                    },
                    {
                        "id": 12,
                        "title": "A Single",
                        "record_type": "single",
                        "release_date": "2026-01-01",
                    },
                ]
            },
            {
                "data": [
                    {"id": 101, "title": "Life", "duration": 241, "track_position": 1},
                    {"id": 102, "title": "ความเชื่อ", "duration": 297, "track_position": 2},
                ]
            },
        ]
    )

    artist = client.resolve_artist("bodyslam")
    albums = client.get_albums(artist.id)

    assert artist.id == "254379"
    assert [album.title for album in albums] == ["Believe"]
    assert [track.title for track in albums[0].tracks] == ["Life", "ความเชื่อ"]
