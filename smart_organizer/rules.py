"""File classification rules for the smart organizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

DEFAULT_RULES: Dict[str, List[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tif"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt",
                  ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".csv"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Code": [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
             ".go", ".rs", ".rb", ".php", ".html", ".css", ".scss", ".json",
             ".xml", ".yaml", ".yml", ".sh", ".sql", ".toml"],
    "Executables": [".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk", ".appimage"],
}


def build_extension_map(rules: Dict[str, List[str]]) -> Dict[str, str]:
    """Flatten {category: [ext, ...]} into {ext: category}."""
    mapping: Dict[str, str] = {}
    for category, extensions in rules.items():
        for ext in extensions:
            mapping[ext.lower()] = category
    return mapping


def validate_category_name(name: str) -> str:
    """Return *name* if it is a safe single-level directory name.

    Category names are joined onto the organized directory, so anything that
    could change that boundary (``..``, absolute paths, drive letters, path
    separators) is rejected instead of silently moving files out of the tree.
    """
    if not isinstance(name, str):
        raise ValueError(f"Category name must be a string, got {type(name).__name__}")
    if not name or not name.strip():
        raise ValueError("Category name must not be empty")
    if name != name.strip():
        raise ValueError(f"Category {name!r} must not start or end with whitespace")
    if name in {".", ".."}:
        raise ValueError(f"Category {name!r} is not allowed")
    if any(char in name for char in ("/", "\\", "\x00")):
        raise ValueError(f"Category {name!r} must be a single directory name")
    if Path(name).is_absolute() or Path(name).drive:
        raise ValueError(f"Category {name!r} must be a relative directory name")
    if name.rstrip(" .") != name:
        raise ValueError(f"Category {name!r} must not end with a dot or a space")
    return name


def load_rules(path: str | Path | None) -> Dict[str, List[str]]:
    """Load rules from a JSON file, or fall back to the built-in defaults."""
    if path is None:
        return {k: list(v) for k, v in DEFAULT_RULES.items()}

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("Rules file must contain a JSON object")

    rules: Dict[str, List[str]] = {}
    for category, extensions in data.items():
        if not isinstance(extensions, list):
            raise ValueError(f"Category '{category}' must map to a list of extensions")
        name = validate_category_name(str(category))
        rules[name] = [str(e).lower() for e in extensions]
    return rules
