import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from ypuller.models import Album, Candidate, Track


class MediaError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def safe_component(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f/\\:*?\"<>|]", "_", value)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned or "unknown"


def ensure_dependencies() -> None:
    missing = []
    if importlib.util.find_spec("yt_dlp") is None:
        missing.append("yt-dlp")
    for command in ("ffmpeg", "ffprobe", "node"):
        if shutil.which(command) is None:
            missing.append(command)
    if missing:
        raise MediaError(f"Missing required tools: {', '.join(missing)}")


class MediaDownloader:
    def __init__(self, runner: Runner = subprocess.run):
        self.runner = runner

    def download(
        self,
        artist: str,
        album: Album,
        track: Track,
        candidate: Candidate,
        output_dir: Path,
    ) -> Path:
        album_dir = output_dir / safe_component(artist) / safe_component(album.title)
        album_dir.mkdir(parents=True, exist_ok=True)
        stem = album_dir / f"{track.number:02d} - {safe_component(track.title)}"
        output_path = stem.with_suffix(".m4a")
        if output_path.exists():
            self.verify_audio_only(output_path)
            return output_path

        download_command = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-config",
            "--no-playlist",
            "--js-runtimes",
            "node",
            "--format",
            "bestaudio[ext=m4a]/bestaudio",
            "--extract-audio",
            "--audio-format",
            "m4a",
            "--audio-quality",
            "0",
            "--output",
            f"{stem}.%(ext)s",
            f"https://www.youtube.com/watch?v={candidate.video_id}",
        ]
        self._run_checked(download_command, "yt-dlp failed")
        if not output_path.is_file():
            raise MediaError(f"yt-dlp did not create the expected file: {output_path}")

        tagged_path = Path(f"{stem}.tagged.m4a")
        tag_command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(output_path),
            "-map",
            "0:a:0",
            "-vn",
            "-c:a",
            "copy",
            "-map_metadata",
            "-1",
            "-metadata",
            f"title={track.title}",
            "-metadata",
            f"artist={artist}",
            "-metadata",
            f"album={album.title}",
            "-metadata",
            f"track={track.number}",
        ]
        if album.year:
            tag_command.extend(["-metadata", f"date={album.year}"])
        tag_command.append(str(tagged_path))

        try:
            self._run_checked(tag_command, "FFmpeg metadata tagging failed")
            os.replace(tagged_path, output_path)
        finally:
            tagged_path.unlink(missing_ok=True)

        self.verify_audio_only(output_path)
        return output_path

    def verify_audio_only(self, path: Path) -> None:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(path),
        ]
        result = self._run_checked(command, "ffprobe failed")
        try:
            streams = json.loads(result.stdout).get("streams", [])
        except json.JSONDecodeError as error:
            raise MediaError(f"ffprobe returned invalid output for {path}") from error
        stream_types = [stream.get("codec_type") for stream in streams]
        if not stream_types or any(stream_type != "audio" for stream_type in stream_types):
            raise MediaError(f"Output is not audio-only: {path}")

    def _run_checked(self, command: list[str], message: str) -> subprocess.CompletedProcess[str]:
        result = self.runner(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = result.stderr.strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            raise MediaError(f"{message}{suffix}")
        return result
