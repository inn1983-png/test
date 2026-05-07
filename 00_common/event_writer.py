from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")

FILENAME = "events.jsonl"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def event_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / FILENAME


def write_event(
    run_dir: str | Path,
    module: str,
    event_type: str,
    stage_id: str | None = None,
    message: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "time": _now_iso(),
        "module": module,
        "stage_id": stage_id,
        "event_type": event_type,
        "message": message,
        "payload": payload or {},
    }
    path = event_path(run_dir)
    io_utils.ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_recent_events(run_dir: str | Path, limit: int = 200) -> list[dict[str, Any]]:
    path = event_path(run_dir)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events
