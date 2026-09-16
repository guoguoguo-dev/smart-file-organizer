"""Tests for the smart file organizer."""

from pathlib import Path

import pytest

from smart_organizer.organizer import Organizer
from smart_organizer.rules import build_extension_map, load_rules


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    (tmp_path / "photo.jpg").write_bytes(b"fake-image")
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "script.py").write_text("print('hi')")
    (tmp_path / "archive.zip").write_bytes(b"PK")
    (tmp_path / "unknown.xyz").write_text("?")
    (tmp_path / ".hidden").write_text("secret")
    return tmp_path


def test_categorize_by_extension():
    org = Organizer()
    assert org.categorize(Path("a.jpg")) == "Images"
    assert org.categorize(Path("a.PNG")) == "Images"
    assert org.categorize(Path("a.py")) == "Code"
    assert org.categorize(Path("a.xyz")) == "Others"


def test_plan_contains_expected_moves(sample_dir: Path):
    plan = Organizer().plan(sample_dir)
    names = {m.src.name for m in plan.moves}
    assert names == {"photo.jpg", "notes.txt", "script.py", "archive.zip", "unknown.xyz"}
    assert ".hidden" not in names


def test_execute_moves_files(sample_dir: Path):
    org = Organizer()
    stats = org.execute(org.plan(sample_dir))
    assert stats["moved"] == 5
    assert (sample_dir / "Images" / "photo.jpg").exists()
    assert (sample_dir / "Code" / "script.py").exists()
    assert (sample_dir / "Others" / "unknown.xyz").exists()


def test_dry_run_keeps_files_in_place(sample_dir: Path):
    org = Organizer()
    org.execute(org.plan(sample_dir), dry_run=True)
    assert (sample_dir / "photo.jpg").exists()
    assert not (sample_dir / "Images").exists()


def test_duplicate_names_get_unique_target(sample_dir: Path):
    (sample_dir / "Images").mkdir()
    (sample_dir / "Images" / "photo.jpg").write_bytes(b"existing")

    plan = Organizer().plan(sample_dir)
    photo_moves = [m for m in plan.moves if m.src.name == "photo.jpg"]
    assert len(photo_moves) == 1
    assert photo_moves[0].dst.name == "photo_1.jpg"


def test_skips_files_already_in_category_folder(sample_dir: Path):
    (sample_dir / "Images").mkdir()
    (sample_dir / "Images" / "nested.png").write_bytes(b"x")
    plan = Organizer().plan(sample_dir)
    assert all(m.src.name != "nested.png" for m in plan.moves)


def test_load_rules_from_json(tmp_path: Path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text('{"Design": [".psd", ".ai"]}')
    assert load_rules(rules_file) == {"Design": [".psd", ".ai"]}


def test_build_extension_map_lowercases():
    mapping = build_extension_map({"Images": [".JPG", ".PNG"]})
    assert mapping == {".jpg": "Images", ".png": "Images"}
