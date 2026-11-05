"""Core file organization engine."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from .rules import DEFAULT_RULES, build_extension_map, validate_category_name


def _path_key(path: Path) -> str:
    """Normalize a path for comparison (case-insensitive on Windows)."""
    return os.path.normcase(str(path))


@dataclass
class Move:
    """A single planned file move."""
    src: Path
    dst: Path
    category: str


@dataclass
class Plan:
    """What the organizer intends to do."""
    moves: List[Move] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)
    # Why a path was left alone (hidden file, already-organized folder, symlink).
    skip_reasons: Dict[Path, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.moves)


@dataclass
class MoveResult:
    """Outcome for a single planned move."""
    src: Path
    dst: Path
    category: str
    status: str  # "moved" (or "would move" during a dry run) / "failed"
    error: str = ""


@dataclass
class ExecutionReport:
    """Per-file outcome plus the aggregate counts derived from it."""
    results: List[MoveResult] = field(default_factory=list)
    skipped: int = 0
    dry_run: bool = False

    @property
    def moved(self) -> int:
        return sum(1 for result in self.results if result.status == "moved")

    @property
    def errors(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    def summary(self) -> Dict[str, int]:
        """Aggregate counts, always consistent with ``results``."""
        return {"moved": self.moved, "errors": self.errors, "skipped": self.skipped}


class Organizer:
    """Organize files into folders based on their extension."""

    def __init__(self, rules: Optional[Dict[str, List[str]]] = None) -> None:
        if rules is None:
            base = {k: list(v) for k, v in DEFAULT_RULES.items()}
        else:
            base = {str(k): list(v) for k, v in rules.items()}
        for name in base:
            validate_category_name(name)
        self.rules = base
        self.ext_map = build_extension_map(self.rules)
        self.category_names = set(self.rules) | {"Others"}

    def categorize(self, path: Path) -> str:
        """Return the category name for a given file."""
        return self.ext_map.get(path.suffix.lower(), "Others")

    def plan(self, source: Path, recursive: bool = False) -> Plan:
        """Build a move plan without touching the filesystem."""
        source = Path(source).expanduser().resolve()
        if not source.is_dir():
            raise NotADirectoryError(f"Not a directory: {source}")

        plan = Plan()
        # Targets already assigned in this plan: two source files must never
        # share a destination, even if the destination does not exist yet.
        reserved: Set[str] = set()
        category_dirs: Dict[str, Path] = {}

        for entry, reason in self._scan(source, recursive):
            if reason is not None:
                plan.skipped.append(entry)
                plan.skip_reasons[entry] = reason
                continue

            category = self.categorize(entry)
            if category not in category_dirs:
                category_dirs[category] = self._category_dir(source, category)
            target = self._unique_target(category_dirs[category] / entry.name, reserved)
            reserved.add(_path_key(target))
            plan.moves.append(Move(src=entry, dst=target, category=category))

        return plan

    def _scan(self, source: Path, recursive: bool) -> Iterator[Tuple[Path, Optional[str]]]:
        """Yield ``(path, skip_reason)`` for everything directly under *source*.

        Directories are pruned before descending, so the subtree of a hidden
        directory, of a root-level category directory, or of a symlinked
        directory is never visited. The source directory itself is never
        treated as a category folder, even when it is named e.g. ``Images``.
        """
        pending: List[Path] = [source]
        while pending:
            current = pending.pop()
            try:
                children = sorted(current.iterdir())
            except OSError:
                continue
            for child in children:
                name = child.name
                if child.is_symlink():
                    yield child, "symlink"
                    continue
                if child.is_dir():
                    if not recursive:
                        continue
                    if name.startswith("."):
                        yield child, "hidden directory"
                        continue
                    if current == source and name in self.category_names:
                        yield child, "already organized"
                        continue
                    pending.append(child)
                    continue
                if name.startswith("."):
                    yield child, "hidden file"
                    continue
                yield child, None

    @staticmethod
    def _category_dir(source: Path, category: str) -> Path:
        """Return the category folder, refusing paths that escape *source*.

        ``resolve()`` also catches an existing category folder that is a
        symlink pointing outside the organized tree.
        """
        target = source / category
        if not target.resolve().is_relative_to(source):
            raise ValueError(
                f"Category {category!r} resolves outside the organized directory"
            )
        return target

    @staticmethod
    def _unique_target(target: Path, reserved: Optional[Set[str]] = None) -> Path:
        """Append a counter to avoid overwriting existing or already-planned files."""
        reserved = reserved if reserved is not None else set()

        def taken(candidate: Path) -> bool:
            return candidate.exists() or _path_key(candidate) in reserved

        if not taken(target):
            return target
        counter = 1
        while True:
            candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
            if not taken(candidate):
                return candidate
            counter += 1

    def execute(self, plan: Plan, dry_run: bool = False) -> Dict[str, int]:
        """Apply a plan. Returns a summary of what happened."""
        return self.execute_detailed(plan, dry_run=dry_run).summary()

    def execute_detailed(self, plan: Plan, dry_run: bool = False) -> ExecutionReport:
        """Apply a plan and report the real outcome of every single move."""
        report = ExecutionReport(skipped=len(plan.skipped), dry_run=dry_run)

        for move in plan.moves:
            if dry_run:
                report.results.append(MoveResult(move.src, move.dst, move.category, "moved"))
                continue
            try:
                move.dst.parent.mkdir(parents=True, exist_ok=True)
                # A file may have appeared at the destination after planning;
                # pick a fresh name instead of silently clobbering it.
                if move.dst.exists():
                    move.dst = self._unique_target(move.dst)
                shutil.move(str(move.src), str(move.dst))
                report.results.append(MoveResult(move.src, move.dst, move.category, "moved"))
            except (OSError, shutil.Error) as exc:
                report.results.append(
                    MoveResult(
                        move.src,
                        move.dst,
                        move.category,
                        "failed",
                        f"{type(exc).__name__}: {exc}",
                    )
                )

        return report
