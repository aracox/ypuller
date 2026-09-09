import json
import subprocess

from ypuller.youtube import YouTubeClient, YouTubeError


def test_searches_with_yt_dlp_and_returns_public_candidates():
    commands = []

    def fake_runner(args, **kwargs):
        commands.append(args)
        payload = {
            "entries": [
                {
                    "id": "video-2",
                    "title": "Two",
                    "channel": "Artist Topic",
                    "duration": 240.4,
                    "availability": "public",
                },
                {
                    "id": "private",
                    "title": "Private",
                    "channel": "Artist",
                    "duration": 180,
                    "availability": "private",
                },
                {
                    "id": "video-1",
                    "title": "One",
                    "uploader": "Artist",
                    "duration": 180,
                    "availability": None,
                },
            ]
        }
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(payload), stderr="")

    candidates = YouTubeClient(runner=fake_runner).search("Artist", "Track")

    assert [candidate.video_id for candidate in candidates] == ["video-2", "video-1"]
    assert candidates[0].duration_seconds == 240
    assert candidates[1].channel == "Artist"
    assert commands[0][commands[0].index("--js-runtimes") + 1] == "node"
    assert commands[0][-1] == "ytsearch5:Artist Track official audio"


def test_raises_a_clear_error_when_yt_dlp_search_fails():
    def fake_runner(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="search unavailable")

    client = YouTubeClient(runner=fake_runner)

    try:
        client.search("Artist", "Track")
    except YouTubeError as error:
        assert str(error) == "yt-dlp search failed: search unavailable"
    else:
        raise AssertionError("expected YouTubeError")
