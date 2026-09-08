"""Local SQLite backup / restore for offline durability (optional polish)."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


BACKUP_GLOBS = (
    "aegis_*.sqlite3",
    "*.sqlite3",
    "geo.json",
)


def _iter_backup_files(data_dir: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in BACKUP_GLOBS:
        for path in sorted(data_dir.glob(pattern)):
            if not path.is_file():
                continue
            if path in seen:
                continue
            seen.add(path)
            yield path


def build_backup_zip(data_dir: Path | str) -> tuple[bytes, dict]:
    """Zip local SQLite + small preference files under data_dir."""
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    files: list[str] = []
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in _iter_backup_files(root):
            arc = path.name
            zf.write(path, arcname=arc)
            files.append(arc)
        meta = (
            f"created_at={datetime.now(timezone.utc).isoformat()}\n"
            f"files={len(files)}\n"
            "note=Local-only backup; restore on the same host.\n"
        )
        zf.writestr("BACKUP_META.txt", meta)
    return buf.getvalue(), {
        "files": files,
        "count": len(files),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def restore_backup_zip(data_dir: Path | str, data: bytes) -> dict:
    """Restore sqlite/json members from a backup zip into data_dir (overwrite)."""
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    if not data:
        raise ValueError("Empty backup")
    restored: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename
            if name.endswith("/") or name == "BACKUP_META.txt":
                continue
            base = Path(name).name
            if not (base.endswith(".sqlite3") or base.endswith(".json")):
                continue
            if ".." in base or "/" in base or "\\" in base:
                continue
            target = root / base
            target.write_bytes(zf.read(info))
            restored.append(base)
    if not restored:
        raise ValueError("No sqlite/json members found in backup")
    return {"restored": restored, "count": len(restored)}
