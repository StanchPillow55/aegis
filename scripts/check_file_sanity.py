from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
HIDDEN_CHARS = ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\ufeff"]

PATTERNS = [
    "backend/**/*.py",
    "importer/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
    "*.txt",
    "Makefile",
    "*.yaml",
    "*.yml",
    "*.md",
    ".github/workflows/*.yml",
]


def iter_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in PATTERNS:
        files.update(ROOT.glob(pattern))
    return sorted(p for p in files if p.is_file())


def main() -> int:
    failed = False

    for path in iter_files():
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")

        for char in HIDDEN_CHARS:
            if char in text:
                print(f"ERROR: hidden unicode {char!r} in {rel}")
                failed = True

        lines = text.splitlines()
        if path.suffix in {".py", ".yaml", ".yml", ".md", ".txt"} or path.name == "Makefile":
            if len(lines) == 1 and len(text) > 120:
                print(f"ERROR: suspicious one-line file: {rel}")
                failed = True

        if path.suffix == ".py":
            try:
                ast.parse(text)
            except SyntaxError as exc:
                print(f"ERROR: Python syntax error in {rel}: {exc}")
                failed = True

    if failed:
        return 1

    print("File sanity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
