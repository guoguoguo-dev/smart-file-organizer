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
        rules[str(category)] = [str(e).lower() for e in extensions]
    return rules
