from ypuller.matcher import select_candidate
from ypuller.models import Candidate, Track

TRACK = Track(id="recording-1", title="ความเชื่อ", number=1, duration_seconds=285)


def test_prefers_official_audio_with_matching_duration():
    official = Candidate(
        video_id="official",
        title="Bodyslam - ความเชื่อ [Official Audio]",
        channel="Bodyslam Official",
        duration_seconds=284,
    )
    unrelated = Candidate(
        video_id="other",
        title="ความเชื่อ - another artist",
        channel="Someone Else",
        duration_seconds=284,
    )

    assert select_candidate("Bodyslam", TRACK, [unrelated, official]) == official


def test_rejects_cover_and_live_variants():
    candidates = [
        Candidate("cover", "Bodyslam ความเชื่อ cover", "Cover Band", 285),
        Candidate("live", "Bodyslam - ความเชื่อ live", "Bodyslam Official", 290),
    ]

    assert select_candidate("Bodyslam", TRACK, candidates) is None


def test_rejects_two_equally_likely_candidates():
    candidates = [
        Candidate("one", "Bodyslam - ความเชื่อ Official Audio", "Bodyslam", 284),
        Candidate("two", "Bodyslam - ความเชื่อ Official Audio", "Bodyslam Topic", 284),
    ]

    assert select_candidate("Bodyslam", TRACK, candidates) is None


def test_prefers_an_exact_artist_channel_over_a_fan_upload():
    official = Candidate("official", "ความเชื่อ", "Bodyslam", 298)
    fan_upload = Candidate(
        "fan",
        "Bodyslam - ความเชื่อ [lyrics]",
        "Song Lyrics X3",
        298,
    )

    assert select_candidate("Bodyslam", TRACK, [fan_upload, official]) == official
