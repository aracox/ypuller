import re
import unicodedata

from ypuller.models import Candidate, Track

_REJECTED_VARIANTS = (
    "cover",
    "karaoke",
    "live",
    "reaction",
    "remix",
    "slowed",
    "sped up",
)


def select_candidate(artist: str, track: Track, candidates: list[Candidate]) -> Candidate | None:
    scored = []
    for candidate in candidates:
        score = _candidate_score(artist, track, candidate)
        if score is not None:
            scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)

    if not scored or scored[0][0] < 90:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] <= 10:
        return None
    return scored[0][1]


def _candidate_score(artist: str, track: Track, candidate: Candidate) -> int | None:
    title = _normalize(candidate.title)
    channel = _normalize(candidate.channel)
    artist_name = _normalize(artist)
    track_title = _normalize(track.title)

    if any(variant in title and variant not in track_title for variant in _REJECTED_VARIANTS):
        return None
    if not track_title or track_title not in title:
        return None

    score = 60
    if artist_name in title:
        score += 25
    if channel == artist_name:
        score += 40
    elif artist_name in channel:
        score += 20
    if "official audio" in title:
        score += 5
    if "official" in channel or "topic" in channel:
        score += 10

    if track.duration_seconds is not None and candidate.duration_seconds is not None:
        difference = abs(track.duration_seconds - candidate.duration_seconds)
        if difference <= 5:
            score += 20
        elif difference <= 15:
            score += 10
        elif difference > 30:
            score -= 30
    return score


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).split())
