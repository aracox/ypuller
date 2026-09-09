import json
import subprocess
from pathlib import Path

from ypuller.media import MediaDownloader, safe_component
from ypuller.models import Album, Candidate, Track


def test_sanitizes_path_components_without_removing_unicode():
    assert safe_component("  ความเชื่อ / demo:  ") == "ความเชื่อ _ demo_"


def test_downloads_tags_and_verifies_audio_only(tmp_path):
    commands = []

    def fake_runner(args, **kwargs):
        commands.append(args)
        if "yt_dlp" in args:
            template = Path(args[args.index("--output") + 1])
            Path(str(template).replace("%(ext)s", "m4a")).write_bytes(b"audio")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[0] == "ffmpeg":
            Path(args[-1]).write_bytes(b"tagged")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps({"streams": [{"codec_type": "audio"}]}),
            stderr="",
        )

    track = Track("recording-1", "ความเชื่อ", 2, 285)
    album = Album("album-1", "Believe", "2005", [track])
    candidate = Candidate("video-1", "title", "channel", 284)
    downloader = MediaDownloader(runner=fake_runner)

    result = downloader.download("Bodyslam", album, track, candidate, tmp_path)

    assert result == tmp_path / "Bodyslam" / "Believe" / "02 - ความเชื่อ.m4a"
    assert result.read_bytes() == b"tagged"
    assert any("title=ความเชื่อ" in command for command in commands[1])
    assert commands[0][commands[0].index("--js-runtimes") + 1] == "node"
    assert commands[-1][0] == "ffprobe"
