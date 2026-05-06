from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_module ON artifacts(module);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_created_at ON artifacts(created_at);
"""


def db_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / "artifacts.db"


def connect(run_dir: str | Path) -> sqlite3.Connection:
    target = db_path(run_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def register_artifact(
    run_dir: str | Path,
    module_name: str,
    artifact_name: str,
    path: str | Path,
    artifact_type: str,
    description: str = "",
    metadata_json: str = "{}",
) -> None:
    run_dir = Path(run_dir)
    target = Path(path)
    try:
        rel_path = str(target.relative_to(run_dir))
    except ValueError:
        rel_path = str(target)

    with connect(run_dir) as conn:
        conn.execute(
            """
            INSERT INTO artifacts(module, name, type, path, description, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                module_name,
                artifact_name,
                artifact_type,
                rel_path,
                description,
                metadata_json,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def find_artifacts(
    run_dir: str | Path,
    module_name: str | None = None,
    artifact_type: str | None = None,
    artifact_name: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if module_name:
        clauses.append("module = ?")
        params.append(module_name)
    if artifact_type:
        clauses.append("type = ?")
        params.append(artifact_type)
    if artifact_name:
        clauses.append("name = ?")
        params.append(artifact_name)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM artifacts {where_sql} ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with connect(run_dir) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def count_artifacts(run_dir: str | Path) -> int:
    with connect(run_dir) as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM artifacts").fetchone()
        return int(row["total"])


def count_by_module(run_dir: str | Path) -> dict[str, int]:
    with connect(run_dir) as conn:
        rows = conn.execute(
            "SELECT module, COUNT(*) AS total FROM artifacts GROUP BY module ORDER BY module"
        ).fetchall()
        return {str(row["module"]): int(row["total"]) for row in rows}


def count_by_type(run_dir: str | Path) -> dict[str, int]:
    with connect(run_dir) as conn:
        rows = conn.execute(
            "SELECT type, COUNT(*) AS total FROM artifacts GROUP BY type ORDER BY type"
        ).fetchall()
        return {str(row["type"]): int(row["total"]) for row in rows}
