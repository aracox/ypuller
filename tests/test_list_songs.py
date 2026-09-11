import sys
from pathlib import Path

# Add project root to sys.path for script imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.list_songs import extract_songs, main, write_song_list


def test_extract_songs_deduplicates_and_sorts(tmp_path: Path):
    downloads = tmp_path / "downloads"
    album1 = downloads / "ArtistB" / "Album1"
    album2 = downloads / "ArtistB" / "BestOf"
    album3 = downloads / "ArtistA" / "Album1"

    album1.mkdir(parents=True)
    album2.mkdir(parents=True)
    album3.mkdir(parents=True)

    (album1 / "01 - Song Two.m4a").write_bytes(b"audio")
    (album2 / "05 - Song Two.m4a").write_bytes(b"audio")  # duplicate in another album
    (album1 / "02 - Song One.m4a").write_bytes(b"audio")
    (album3 / "01 - Alpha.m4a").write_bytes(b"audio")
    (downloads / "ArtistB" / ".ypuller-manifest.json").write_text("{}", encoding="utf-8")

    songs = extract_songs(downloads)

    assert songs == [
        ("ArtistA", "Alpha"),
        ("ArtistB", "Song One"),
        ("ArtistB", "Song Two"),
    ]


def test_write_song_list_format(tmp_path: Path):
    output_file = tmp_path / "song.txt"
    songs = [("Labanoon", "บอกแล้ว"), ("Loso", "ใจสั่งมา")]

    write_song_list(songs, output_file)

    content = output_file.read_text(encoding="utf-8")
    assert content == "[Labanoon,บอกแล้ว]\n[Loso,ใจสั่งมา]\n"


def test_main_cli(tmp_path: Path, capsys):
    downloads = tmp_path / "downloads"
    album = downloads / "Bodyslam" / "Believe"
    album.mkdir(parents=True)
    (album / "01 - Life.m4a").write_bytes(b"audio")

    exit_code = main([str(downloads)])

    assert exit_code == 0
    song_txt = downloads / "song.txt"
    assert song_txt.is_file()
    assert song_txt.read_text(encoding="utf-8") == "[Bodyslam,Life]\n"

    captured = capsys.readouterr()
    assert "Found 1 unique songs across 1 artists." in captured.out
