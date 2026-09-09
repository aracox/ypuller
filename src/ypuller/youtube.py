import json
import subprocess
import sys
from collections.abc import Callable

from ypuller.models import Candidate


class YouTubeError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


class YouTubeClient:
    def __init__(self, runner: Runner = subprocess.run):
        self.runner = runner

    def search(self, artist: str, track: str) -> list[Candidate]:
        query = f"ytsearch5:{artist} {track} official audio"
        command = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-config",
            "--flat-playlist",
            "--dump-single-json",
            "--js-runtimes",
            "node",
            query,
        ]
        result = self.runner(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            details = result.stderr.strip().splitlines()
            suffix = f": {details[-1]}" if details else ""
            raise YouTubeError(f"yt-dlp search failed{suffix}")

        try:
            entries = json.loads(result.stdout).get("entries") or []
        except (AttributeError, json.JSONDecodeError) as error:
            raise YouTubeError("yt-dlp search returned invalid metadata") from error

        candidates = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            video_id = entry.get("id")
            title = entry.get("title")
            availability = entry.get("availability")
            if not video_id or not title or availability not in (None, "public", "unlisted"):
                continue
            candidates.append(
                Candidate(
                    video_id=video_id,
                    title=title,
                    channel=entry.get("channel") or entry.get("uploader") or "",
                    duration_seconds=_duration(entry.get("duration")),
                )
            )
        return candidates


def _duration(value: object) -> int | None:
    try:
        return round(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None
