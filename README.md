# Smart File Organizer

A tiny command-line tool that sorts messy folders into clean, predictable categories.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Why

The Downloads folder is where files go to die. `smart-organizer` puts each one
into a folder that matches its type — `Images/`, `Documents/`, `Code/`, and so on.

## Features

- **Rule-based sorting** — one JSON file controls everything
- **Dry-run mode** — see what will happen before it happens
- **Safe by default** — never overwrites; appends `_1`, `_2`, ... on collisions
- **Idempotent** — running it twice is harmless
- **Zero dependencies** — pure standard library

## Installation

```bash
git clone https://github.com/guoguoguo-dev/smart-file-organizer.git
cd smart-file-organizer
pip install -e .
```

## Usage

Preview what would happen:

```bash
smart-organizer ~/Downloads --dry-run
```

Actually organize:

```bash
smart-organizer ~/Downloads
```

Recurse into subfolders with a custom rule set:

```bash
smart-organizer ~/Downloads -r -c my-rules.json
```

Show the active rules:

```bash
smart-organizer --list-rules
```

## Custom rules

Create a JSON file mapping category names to extension lists. Anything not listed
falls into `Others/`.

```json
{
  "Design": [".psd", ".ai", ".fig", ".sketch"],
  "Notebooks": [".ipynb"],
  "Data": [".csv", ".parquet", ".json"]
}
```

## How it works

1. `plan()` scans the directory and builds `Move` objects. Nothing touches disk.
2. `execute()` walks the plan, creating folders and moving files.
3. Name collisions are resolved with a counter, so nothing is ever overwritten.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
