from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from importlib import import_module

io_utils = import_module("00_common.io_utils")

SCHEMA_VERSION = "1.0"
PROBLEM_FIELDS = {
    "needs_retry",
    "needs_review",
    "retry_plan",
    "retry_stages",
    "upstream_blocking_issues",
    "schema_validation_issues",
    "failed_frames",
    "failed_audio_segments",
    "failed_video_segments",
    "missing_segments",
    "invalid_segments",
}
PIPELINE_ORDER = [
    "00_main_controller",
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _rel(run_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(run_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _iter_json_files(run_dir: Path) -> Iterable[Path]:
    patterns = [
        "run_status.json",
        "*/intermediate/*.json",
        "*/*_meta.json",
        "*/*_manifest.json",
        "*/image_manifest.json",
        "*/audio_manifest.json",
        "*/video_manifest.json",
    ]
    seen: set[Path] = set()
    for pattern in patterns:
        for path in run_dir.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def _module_from_path(run_dir: Path, path: Path) -> str | None:
    if path.name == "run_status.json":
        return None
    try:
        parts = path.relative_to(run_dir).parts
    except ValueError:
        return None
    return parts[0] if parts else None


def _stage_from_text(value: Any) -> str | None:
    text = str(value or "")
    match = re.search(r"\b(\d{2}[A-Z])\b", text)
    return match.group(1) if match else (text or None)


def _stage_from_data(path: Path, data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("stage_id", "current_stage_id", "stage"):
            stage = _stage_from_text(data.get(key))
            if stage:
                return stage
    return _stage_from_text(path.name)


def _has_problem_value(field: str, value: Any) -> bool:
    if value in (None, False, "", [], {}):
        return False
    if field in {"needs_retry", "needs_review"}:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "retry", "review", "needs_retry", "needs_review"}
        return value is True
    if field == "retry_plan" and isinstance(value, dict):
        if value.get("needs_retry") is True or value.get("needs_review") is True:
            return True
        for key in ("failed_frame_ids", "failed_segment_ids", "retry_stages", "missing_segments", "invalid_segments"):
            if value.get(key):
                return True
        return False
    return bool(value)


def _summarize_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        keys = ", ".join(list(value.keys())[:8])
        return f"object keys: {keys}" if keys else "object"
    text = str(value)
    return text[:240] + ("..." if len(text) > 240 else "")


def _walk_problem_fields(data: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, Any, tuple[str, ...]]]:
    if isinstance(data, dict):
        for key, value in data.items():
            child_path = (*path, str(key))
            if key in PROBLEM_FIELDS and _has_problem_value(key, value):
                yield key, value, child_path
            yield from _walk_problem_fields(value, child_path)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            yield from _walk_problem_fields(item, (*path, str(index)))


def _run_status_issues(run_dir: Path, data: Any, path: Path) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    modules = data.get("modules", {})
    if not isinstance(modules, dict):
        return []
    issues: list[dict[str, Any]] = []
    for module_name, item in modules.items():
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in {"failed", "blocked"}:
            continue
        issues.append(
            {
                "module": module_name,
                "stage": None,
                "file": _rel(run_dir, path),
                "field": "run_status",
                "summary": str(item.get("message") or status),
                "value_summary": str(status),
                "severity": "error",
            }
        )
    return issues


def _json_file_issues(run_dir: Path, path: Path, data: Any) -> list[dict[str, Any]]:
    module_name = _module_from_path(run_dir, path)
    stage = _stage_from_data(path, data)
    issues: list[dict[str, Any]] = []
    for field, value, field_path in _walk_problem_fields(data):
        issues.append(
            {
                "module": module_name,
                "stage": stage,
                "file": _rel(run_dir, path),
                "field": field,
                "json_path": ".".join(field_path),
                "summary": f"{field}: {_summarize_value(value)}",
                "value_summary": _summarize_value(value),
                "severity": "warning" if field in {"needs_review", "schema_validation_issues"} else "error",
            }
        )
    return issues


def _issue_sort_key(issue: dict[str, Any]) -> tuple[int, int, str]:
    order = {module: index for index, module in enumerate(PIPELINE_ORDER)}
    module_index = order.get(str(issue.get("module") or ""), len(order))
    stage = str(issue.get("stage") or "")
    stage_match = re.search(r"(\d{2})([A-Z])", stage)
    stage_index = len("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if stage_match:
        stage_index = max(0, ord(stage_match.group(2)) - ord("A"))
    return module_index, stage_index, str(issue.get("file") or "")


def _recommended_command(run_dir: Path, module_name: str | None) -> str:
    if not module_name:
        return ""
    context = io_utils.read_json(run_dir / "runtime_context.json", default={})
    if not isinstance(context, dict):
        context = {}
    mode = context.get("mode") or "project"
    if mode == "book_chapter":
        book_id = context.get("book_id")
        chapter_id = context.get("chapter_id")
        if book_id and chapter_id:
            return (
                "python 00_main_controller/run_pipeline.py "
                f"--mode book_chapter --book-id {book_id} --chapter-id {chapter_id} --only-module {module_name}"
            )
    project_id = context.get("project_id") or run_dir.name
    return f"python 00_main_controller/run_pipeline.py --mode project --project-id {project_id} --only-module {module_name}"


def build_repair_index(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    issues: list[dict[str, Any]] = []
    if not run_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "run_dir": str(run_path),
            "earliest_problem_module": None,
            "earliest_problem_stage": None,
            "recommended_action": "none",
            "recommended_command": "",
            "issues": [],
            "error": "run_dir not found",
        }

    for path in _iter_json_files(run_path):
        data = io_utils.read_json(path, default=None)
        if path.name == "run_status.json":
            issues.extend(_run_status_issues(run_path, data, path))
        issues.extend(_json_file_issues(run_path, path, data))

    issues = sorted(issues, key=_issue_sort_key)
    earliest = issues[0] if issues else {}
    earliest_module = earliest.get("module")
    earliest_stage = earliest.get("stage")
    recommended_action = "rerun_module" if earliest_module else "none"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "run_dir": str(run_path),
        "earliest_problem_module": earliest_module,
        "earliest_problem_stage": earliest_stage,
        "recommended_action": recommended_action,
        "recommended_command": _recommended_command(run_path, earliest_module),
        "issues": issues,
    }


def write_repair_index(run_dir: str | Path) -> dict[str, Any]:
    data = build_repair_index(run_dir)
    io_utils.write_json(Path(run_dir) / "repair_index.json", data)
    return data
