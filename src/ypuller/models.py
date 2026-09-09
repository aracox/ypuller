from dataclasses import dataclass


@dataclass(frozen=True)
class Artist:
    id: str
    name: str


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    number: int
    duration_seconds: int | None


@dataclass(frozen=True)
class Album:
    id: str
    title: str
    year: str
    tracks: list[Track]


@dataclass(frozen=True)
class Candidate:
    video_id: str
    title: str
    channel: str
    duration_seconds: int | None
