from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")
event_writer = import_module("00_common.event_writer")

FILENAME = "current_stage_status.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _path(output_dir: str | Path) -> Path:
    return Path(output_dir) / FILENAME


def _run_dir_from_output(output_dir: str | Path) -> Path:
    return Path(output_dir).parent


def mark_stage_started(
    module: str,
    output_dir: str | Path,
    stage_id: str,
    stage_name: str,
    message: str = "",
) -> dict[str, Any]:
    data = {
        "module": module,
        "current_stage_id": stage_id,
        "current_stage_name": stage_name,
        "status": "running",
        "started_at": _now_iso(),
        "message": message,
    }
    io_utils.write_json(_path(output_dir), data)
    event_writer.write_event(
        _run_dir_from_output(output_dir),
        module=module,
        stage_id=stage_id,
        event_type="stage_started",
        message=message or f"stage started: {stage_id}",
        payload={"stage_name": stage_name},
    )
    return data


def mark_stage_finished(
    module: str,
    output_dir: str | Path,
    stage_id: str,
    stage_name: str,
    status: str,
    output_file: str | None = None,
    score: int | float | None = None,
    issues_count: int | None = None,
    message: str = "",
) -> dict[str, Any]:
    current = io_utils.read_json(_path(output_dir), default={})
    if not isinstance(current, dict) or current.get("current_stage_id") != stage_id:
        current = {}
    started_at = current.get("started_at") or _now_iso()
    ended_at = _now_iso()
    start_dt = _parse_iso(started_at)
    end_dt = _parse_iso(ended_at)
    duration_seconds = round((end_dt - start_dt).total_seconds(), 3) if start_dt and end_dt else 0
    data = {
        "module": module,
        "current_stage_id": stage_id,
        "current_stage_name": stage_name,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "output_file": output_file or "",
        "score": score,
        "issues_count": issues_count,
        "message": message,
    }
    io_utils.write_json(_path(output_dir), data)
    event_writer.write_event(
        _run_dir_from_output(output_dir),
        module=module,
        stage_id=stage_id,
        event_type="stage_finished",
        message=message or f"stage finished: {stage_id}",
        payload={
            "stage_name": stage_name,
            "status": status,
            "output_file": output_file or "",
            "score": score,
            "issues_count": issues_count,
            "duration_seconds": duration_seconds,
        },
    )
    return data


def mark_stage_failed(
    module: str,
    output_dir: str | Path,
    stage_id: str,
    stage_name: str,
    message: str,
) -> dict[str, Any]:
    return mark_stage_finished(
        module=module,
        output_dir=output_dir,
        stage_id=stage_id,
        stage_name=stage_name,
        status="failed",
        output_file=None,
        score=None,
        issues_count=1,
        message=message,
    )
