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


def test_recursive_prunes_hidden_and_category_subtrees(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]")
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "data.bin").write_bytes(b"x")
    (tmp_path / "Images" / "nested").mkdir(parents=True)
    (tmp_path / "Images" / "nested" / "photo.jpg").write_bytes(b"jpg")
    (tmp_path / "notes.txt").write_text("hi")

    plan = Organizer().plan(tmp_path, recursive=True)

    assert [m.src.relative_to(tmp_path).as_posix() for m in plan.moves] == ["notes.txt"]
    assert plan.skip_reasons[tmp_path / ".git"] == "hidden directory"
    assert plan.skip_reasons[tmp_path / ".cache"] == "hidden directory"
    assert plan.skip_reasons[tmp_path / "Images"] == "already organized"


def test_root_directory_named_like_category_is_still_organized(tmp_path: Path):
    root = tmp_path / "Images"
    root.mkdir()
    (root / "report.txt").write_text("content")

    plan = Organizer().plan(root)

    assert [m.src.name for m in plan.moves] == ["report.txt"]
    assert plan.moves[0].dst == root / "Documents" / "report.txt"


def test_same_name_directory_outside_category_area_is_walked(tmp_path: Path):
    nested = tmp_path / "photos" / "Images"
    nested.mkdir(parents=True)
    (nested / "pic.png").write_bytes(b"x")

    plan = Organizer().plan(tmp_path, recursive=True)

    assert [m.src.relative_to(tmp_path).as_posix() for m in plan.moves] == ["photos/Images/pic.png"]


def test_hidden_file_records_reason(tmp_path: Path):
    (tmp_path / ".secret").write_text("x")
    plan = Organizer().plan(tmp_path)
    assert tmp_path / ".secret" in plan.skipped
    assert plan.skip_reasons[tmp_path / ".secret"] == "hidden file"


def test_same_name_files_in_different_directories_are_all_kept(tmp_path: Path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "report.txt").write_text("from-a")
    (tmp_path / "b" / "report.txt").write_text("from-b")

    org = Organizer()
    plan = org.plan(tmp_path, recursive=True)
    destinations = [move.dst for move in plan.moves]
    assert len(destinations) == len(set(destinations)) == 2

    stats = org.execute(plan)
    assert stats == {"moved": 2, "errors": 0, "skipped": 0}
    assert sorted(p.read_text() for p in (tmp_path / "Documents").iterdir()) == ["from-a", "from-b"]


def test_planned_targets_reserved_alongside_existing_files(tmp_path: Path):
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "report.txt").write_text("existing")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "report.txt").write_text("from-a")
    (tmp_path / "b" / "report.txt").write_text("from-b")

    plan = Organizer().plan(tmp_path, recursive=True)
    assert sorted(move.dst.name for move in plan.moves) == ["report_1.txt", "report_2.txt"]


def test_execute_keeps_file_created_after_planning(tmp_path: Path):
    (tmp_path / "photo.jpg").write_text("planned")
    org = Organizer()
    plan = org.plan(tmp_path)

    target = tmp_path / "Images" / "photo.jpg"
    target.parent.mkdir()
    target.write_text("appeared-later")

    stats = org.execute(plan)
    assert stats == {"moved": 1, "errors": 0, "skipped": 0}
    assert target.read_text() == "appeared-later"
    assert (tmp_path / "Images" / "photo_1.jpg").read_text() == "planned"


def test_load_rules_from_json(tmp_path: Path):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text('{"Design": [".psd", ".ai"]}')
    assert load_rules(rules_file) == {"Design": [".psd", ".ai"]}


def test_build_extension_map_lowercases():
    mapping = build_extension_map({"Images": [".JPG", ".PNG"]})
    assert mapping == {".jpg": "Images", ".png": "Images"}
