"""Core file organization engine."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .rules import DEFAULT_RULES, build_extension_map


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

    @property
    def total(self) -> int:
        return len(self.moves)


class Organizer:
    """Organize files into folders based on their extension."""

    def __init__(self, rules: Optional[Dict[str, List[str]]] = None) -> None:
        self.rules = rules if rules is not None else {k: list(v) for k, v in DEFAULT_RULES.items()}
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
        entries: Iterable[Path] = source.rglob("*") if recursive else source.iterdir()

        for entry in entries:
            if not entry.is_file():
                continue
            # Skip hidden files and files already inside a category folder
            if entry.name.startswith(".") or entry.parent.name in self.category_names:
                plan.skipped.append(entry)
                continue

            category = self.categorize(entry)
            target = self._unique_target(source / category / entry.name)
            plan.moves.append(Move(src=entry, dst=target, category=category))

        return plan

    @staticmethod
    def _unique_target(target: Path) -> Path:
        """Append a counter to avoid overwriting existing files."""
        if not target.exists():
            return target
        counter = 1
        while True:
            candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def execute(self, plan: Plan, dry_run: bool = False) -> Dict[str, int]:
        """Apply a plan. Returns a summary of what happened."""
        stats = {"moved": 0, "errors": 0, "skipped": len(plan.skipped)}

        for move in plan.moves:
            if dry_run:
                stats["moved"] += 1
                continue
            try:
                move.dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(move.src), str(move.dst))
                stats["moved"] += 1
            except (OSError, shutil.Error):
                stats["errors"] += 1

        return stats
