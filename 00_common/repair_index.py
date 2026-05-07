from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from importlib import import_module

io_utils = import_module("00_common.io_utils")

SCHEMA_VERSION = "1.1"
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
ISSUE_TYPE_MAP = {
    "needs_retry": "stage_quality_failed",
    "needs_review": "stage_quality_failed",
    "retry_plan": "stage_quality_failed",
    "retry_stages": "stage_quality_failed",
    "upstream_blocking_issues": "upstream_blocking",
    "schema_validation_issues": "schema_failed",
    "failed_frames": "image_failed_frames",
    "failed_audio_segments": "audio_failed_segments",
    "failed_video_segments": "video_failed_segments",
    "missing_segments": "missing_dependency",
    "invalid_segments": "missing_dependency",
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
MODULE_RETRY_SCOPE = {
    "07_storyboard_image": {"issue_type": "image_failed_frames", "retry_key": "image_retry_scope", "retry_value": "failed_frames"},
    "08_audio": {"issue_type": "audio_failed_segments", "retry_key": "audio_retry_scope", "retry_value": "failed_segments"},
    "09_video": {"issue_type": "video_failed_segments", "retry_key": "video_retry_scope", "retry_value": "failed_segments"},
}


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


def _classify_issue_type(field: str, value: Any, module_name: str | None) -> str:
    if field == "upstream_blocking_issues":
        return "upstream_blocking"
    if field == "schema_validation_issues":
        return "schema_failed"
    if field == "failed_frames":
        return "image_failed_frames"
    if field == "failed_audio_segments":
        return "audio_failed_segments"
    if field == "failed_video_segments":
        return "video_failed_segments"
    if field in {"missing_segments", "invalid_segments"}:
        return "missing_dependency"
    if module_name == "10_final_assembly" and field in {"needs_review", "needs_retry"}:
        return "final_export_not_ready"
    if field in {"needs_retry", "needs_review", "retry_plan", "retry_stages"}:
        return "stage_quality_failed"
    return ISSUE_TYPE_MAP.get(field, "stage_quality_failed")


def _suggest_action(issue_type: str, module_name: str | None) -> str:
    if issue_type == "upstream_blocking":
        return "rerun_from_upstream"
    if issue_type == "missing_dependency":
        return "rerun_from_upstream"
    if issue_type == "image_failed_frames":
        return "retry_failed_frames"
    if issue_type == "audio_failed_segments":
        return "retry_failed_segments"
    if issue_type == "video_failed_segments":
        return "retry_failed_segments"
    if issue_type == "final_export_not_ready":
        return "check_ffmpeg_and_upstream"
    if issue_type == "schema_failed":
        return "rerun_module"
    if issue_type == "stage_quality_failed":
        return "rerun_module"
    return "rerun_module"


def _recommended_from(module_name: str | None, issue_type: str) -> str | None:
    if not module_name:
        return None
    if issue_type in {"upstream_blocking", "missing_dependency"}:
        order = {m: i for i, m in enumerate(PIPELINE_ORDER)}
        idx = order.get(module_name, len(order))
        if idx > 1:
            return PIPELINE_ORDER[max(1, idx - 1)]
        return module_name
    return module_name


def _recommended_only(module_name: str | None, issue_type: str) -> str | None:
    if not module_name:
        return None
    if issue_type in {"upstream_blocking", "missing_dependency"}:
        return None
    return module_name


def _can_run_current(module_name: str | None, issue_type: str) -> bool:
    if not module_name:
        return False
    return issue_type not in {"upstream_blocking", "missing_dependency"}


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
        issue_type = "upstream_blocking" if status == "blocked" else "stage_quality_failed"
        suggested_action = _suggest_action(issue_type, module_name)
        issues.append(
            {
                "module": module_name,
                "stage_id": None,
                "status": status,
                "score": None,
                "issue_type": issue_type,
                "issue_message": str(item.get("message") or status),
                "suggested_action": suggested_action,
                "recommended_from_module": _recommended_from(module_name, issue_type),
                "recommended_only_module": _recommended_only(module_name, issue_type),
                "can_run_current_module": _can_run_current(module_name, issue_type),
                "file": _rel(run_dir, path),
                "field": "run_status",
                "payload": {},
            }
        )
    return issues


def _json_file_issues(run_dir: Path, path: Path, data: Any) -> list[dict[str, Any]]:
    module_name = _module_from_path(run_dir, path)
    stage = _stage_from_data(path, data)
    score = None
    if isinstance(data, dict):
        quality = data.get("stage_quality") or data.get("quality_report") or {}
        if isinstance(quality, dict):
            score = quality.get("score")
    issues: list[dict[str, Any]] = []
    for field, value, field_path in _walk_problem_fields(data):
        issue_type = _classify_issue_type(field, value, module_name)
        suggested_action = _suggest_action(issue_type, module_name)
        issues.append(
            {
                "module": module_name,
                "stage_id": stage,
                "status": "needs_review" if field in {"needs_review", "schema_validation_issues"} else "failed",
                "score": score,
                "issue_type": issue_type,
                "issue_message": f"{field}: {_summarize_value(value)}",
                "suggested_action": suggested_action,
                "recommended_from_module": _recommended_from(module_name, issue_type),
                "recommended_only_module": _recommended_only(module_name, issue_type),
                "can_run_current_module": _can_run_current(module_name, issue_type),
                "file": _rel(run_dir, path),
                "field": field,
                "json_path": ".".join(field_path),
                "payload": {"value_summary": _summarize_value(value)},
            }
        )
    return issues


def _final_export_issues(run_dir: Path) -> list[dict[str, Any]]:
    final_dir = run_dir / "10_final_assembly"
    manifest_path = final_dir / "final_manifest.json"
    if not manifest_path.exists():
        return []
    data = io_utils.read_json(manifest_path, default=None)
    if not isinstance(data, dict):
        return []
    final_video_ready = data.get("final_video_ready")
    if final_video_ready is True:
        return []
    return [
        {
            "module": "10_final_assembly",
            "stage_id": "10D",
            "status": "needs_review",
            "score": None,
            "issue_type": "final_export_not_ready",
            "issue_message": f"最终视频未生成 (final_video_ready={final_video_ready})",
            "suggested_action": "check_ffmpeg_and_upstream",
            "recommended_from_module": "09_video",
            "recommended_only_module": None,
            "can_run_current_module": False,
            "file": _rel(run_dir, manifest_path),
            "field": "final_video_ready",
            "payload": {
                "final_video_ready": final_video_ready,
                "final_video_placeholder_path": data.get("final_video_placeholder_path"),
            },
        }
    ]


def _dependency_issues(run_dir: Path) -> list[dict[str, Any]]:
    try:
        module_contracts = import_module("00_common.module_contracts")
    except Exception:
        return []
    contracts = module_contracts.load_contracts()
    issues: list[dict[str, Any]] = []
    for module_name in PIPELINE_ORDER[1:]:
        try:
            result = module_contracts.inspect_module_requirements(run_dir, module_name, contracts)
            if isinstance(result, dict) and not result.get("can_run", True):
                missing = result.get("missing_requires", [])
                for item in missing:
                    if isinstance(item, dict):
                        upstream = item.get("module", "")
                        artifact = item.get("name", "")
                        issues.append({
                            "module": module_name,
                            "stage_id": None,
                            "status": "blocked",
                            "score": None,
                            "issue_type": "missing_dependency",
                            "issue_message": f"缺少上游产物：{upstream}.{artifact}",
                            "suggested_action": "rerun_from_upstream",
                            "recommended_from_module": upstream or module_name,
                            "recommended_only_module": None,
                            "can_run_current_module": False,
                            "file": "",
                            "field": "missing_dependency",
                            "payload": {"upstream_module": upstream, "artifact_name": artifact},
                        })
        except Exception:
            pass
    return issues


def _issue_sort_key(issue: dict[str, Any]) -> tuple[int, int, str]:
    order = {module: index for index, module in enumerate(PIPELINE_ORDER)}
    module_index = order.get(str(issue.get("module") or ""), len(order))
    stage = str(issue.get("stage_id") or issue.get("stage") or "")
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
            "summary": {"total_issues": 0, "blocking_issues": 0, "retryable_issues": 0, "recommended_from_module": None},
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

    issues.extend(_final_export_issues(run_path))
    issues.extend(_dependency_issues(run_path))

    issues = sorted(issues, key=_issue_sort_key)
    blocking = [i for i in issues if not i.get("can_run_current_module", True)]
    retryable = [i for i in issues if i.get("can_run_current_module", True)]
    earliest = issues[0] if issues else {}
    earliest_module = earliest.get("recommended_from_module") or earliest.get("module")
    recommended_action = earliest.get("suggested_action", "none") if earliest else "none"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "run_dir": str(run_path),
        "summary": {
            "total_issues": len(issues),
            "blocking_issues": len(blocking),
            "retryable_issues": len(retryable),
            "recommended_from_module": earliest_module,
        },
        "earliest_problem_module": earliest.get("module"),
        "earliest_problem_stage": earliest.get("stage_id"),
        "recommended_action": recommended_action,
        "recommended_command": _recommended_command(run_path, earliest_module),
        "issues": issues,
    }


def write_repair_index(run_dir: str | Path) -> dict[str, Any]:
    data = build_repair_index(run_dir)
    io_utils.write_json(Path(run_dir) / "repair_index.json", data)
    return data
