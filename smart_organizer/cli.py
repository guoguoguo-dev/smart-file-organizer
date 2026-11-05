"""Command-line interface for the smart file organizer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .organizer import Organizer
from .rules import load_rules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smart-organizer",
        description="Organize files into folders by type.",
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="Directory to organize (default: current directory)")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Recurse into subdirectories")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Preview the changes without moving anything")
    parser.add_argument("-c", "--config", type=Path,
                        help="Path to a JSON file with custom rules")
    parser.add_argument("--list-rules", action="store_true",
                        help="Print the active rules and exit")
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_rules:
        for category, exts in rules.items():
            print(f"{category}: {', '.join(exts)}")
        return 0

    organizer = Organizer(rules)

    try:
        plan = organizer.plan(Path(args.path), recursive=args.recursive)
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not plan.moves:
        print("Nothing to organize. ✨")
        return 0

    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}Plan: {plan.total} file(s)")
    for move in plan.moves:
        print(f"  {move.src.name}  ->  {move.category}/")

    if args.dry_run:
        print("\nDry run — no files were moved.")
        return 0

    stats = organizer.execute(plan)
    print(f"\nDone. Moved: {stats['moved']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
    return 0 if stats["errors"] == 0 else 1
