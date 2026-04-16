from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    db_path: Path


def get_paths(root: Path | None = None) -> Paths:
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    data_dir = root / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    db_path = data_dir / "campus.db"
    return Paths(root=root, data_dir=data_dir, raw_dir=raw_dir, processed_dir=processed_dir, db_path=db_path)

