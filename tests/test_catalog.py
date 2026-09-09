from ypuller.catalog import MusicBrainzClient


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
