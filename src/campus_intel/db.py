from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def exec_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()

