from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")

STATUS_FILENAME = "run_status.json"


def status_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / STATUS_FILENAME


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_status(run_dir: str | Path) -> dict[str, Any]:
    data = io_utils.read_json(status_path(run_dir), default={})
    return data if isinstance(data, dict) else {}


def save_status(run_dir: str | Path, data: dict[str, Any]) -> None:
    io_utils.write_json(status_path(run_dir), data)


def initialize_status(run_dir: str | Path, pipeline: list[str]) -> None:
    """Initialize run_status.json while preserving existing module history when possible."""
    data = load_status(run_dir)
    data.setdefault("created_at", now_iso())
    data["updated_at"] = now_iso()
    data["pipeline"] = pipeline
    modules = data.setdefault("modules", {})
    for module_name in pipeline:
        modules.setdefault(
            module_name,
            {
                "status": "pending",
                "start_time": None,
                "end_time": None,
                "duration_seconds": None,
                "return_code": None,
                "message": "waiting",
            },
        )
    save_status(run_dir, data)


def mark_module(
    run_dir: str | Path,
    module_name: str,
    status: str,
    start_time: str | None = None,
    end_time: str | None = None,
    duration_seconds: float | None = None,
    return_code: int | None = None,
    message: str | None = None,
) -> None:
    data = load_status(run_dir)
    data.setdefault("created_at", now_iso())
    data["updated_at"] = now_iso()
    modules = data.setdefault("modules", {})
    item = modules.setdefault(module_name, {})

    item["status"] = status
    if start_time is not None:
        item["start_time"] = start_time
    if end_time is not None:
        item["end_time"] = end_time
    if duration_seconds is not None:
        item["duration_seconds"] = duration_seconds
    if return_code is not None:
        item["return_code"] = return_code
    if message is not None:
        item["message"] = message

    save_status(run_dir, data)


def mark_skipped(run_dir: str | Path, module_name: str, message: str) -> None:
    mark_module(
        run_dir=run_dir,
        module_name=module_name,
        status="skipped",
        end_time=now_iso(),
        return_code=0,
        message=message,
    )
