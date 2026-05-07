from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def should_skip_stage(
    output_dir: str | Path,
    stage_id: str,
    output_file: str,
    force: bool = False,
    force_stages: list[str] | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    if force:
        return False, None
    if force_stages and stage_id in force_stages:
        return False, None

    intermediate_dir = Path(output_dir) / "intermediate"
    stage_path = intermediate_dir / output_file
    if not stage_path.exists():
        return False, None

    data = io_utils.read_json(stage_path, default=None)
    if not isinstance(data, dict):
        return False, None

    stage_quality = data.get("stage_quality", {})
    if not isinstance(stage_quality, dict):
        return False, None

    passed = stage_quality.get("passed")
    if passed is not True:
        return False, None

    schema_version = data.get("schema_version")
    if not schema_version:
        return False, None

    return True, data


def load_cached_outputs(
    output_dir: str | Path,
    stages: list[dict[str, str]],
    force: bool = False,
    force_stages: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for stage in stages:
        stage_id = stage["stage_id"]
        skip, data = should_skip_stage(output_dir, stage_id, stage["output_file"], force=force, force_stages=force_stages)
        if skip and data is not None:
            outputs[stage_id] = data
    return outputs


def find_resume_start_index(
    stages: list[dict[str, str]],
    cached_outputs: dict[str, dict[str, Any]],
    stage_index: dict[str, int],
) -> int:
    last_passed_index = -1
    for stage in stages:
        stage_id = stage["stage_id"]
        if stage_id in cached_outputs:
            last_passed_index = stage_index[stage_id]
    if last_passed_index < 0:
        return 0
    return last_passed_index + 1


def parse_force_stages(force_stage_arg: str | None) -> list[str] | None:
    if not force_stage_arg:
        return None
    return [s.strip() for s in force_stage_arg.split(",") if s.strip()]


def add_resume_args(parser: Any) -> None:
    parser.add_argument("--resume", action="store_true", default=_env_bool("AI_DRAMA_RESUME", False), help="Skip stages whose intermediate output already passed quality check.")
    parser.add_argument("--force", action="store_true", default=False, help="Force rerun all stages, ignoring cached outputs.")
    parser.add_argument("--force-stage", default=None, help="Comma-separated stage IDs to force rerun (e.g. 01C,01D).")
