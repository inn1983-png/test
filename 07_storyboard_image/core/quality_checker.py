from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "07P": ["character_lock_tasks", "appearance_tasks", "reference_asset_tasks", "storyboard_frame_tasks", "dependency_index"],
    "07A": ["character_locks", "character_lock_manifest", "execution_summary"],
    "07B": ["appearances", "appearance_manifest", "execution_summary"],
    "07C": ["reference_assets", "reference_asset_manifest", "execution_summary"],
    "07D": ["images", "image_manifest", "execution_summary"],
    "07E": ["asset_image_registry", "dependency_index", "retry_plan", "quality_report", "storyboard_image_meta"],
}


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _check_rows(stage_id: str, rows: Any, required: list[str], label: str, issues: list[str]) -> int:
    penalty = 0
    if not isinstance(rows, list):
        issues.append(f"{label} 必须为数组")
        return 20
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"{label}[{idx}] 不是对象")
            penalty += 8
            continue
        for field in required:
            if field not in row:
                issues.append(f"{stage_id} {label}[{idx}] 缺少字段：{field}")
                penalty += 4
    return penalty


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18

    if stage_id == "07P":
        score -= _check_rows(stage_id, data.get("character_lock_tasks", []), ["task_id", "lock_key", "canonical_name", "status"], "character_lock_tasks", issues)
        score -= _check_rows(stage_id, data.get("appearance_tasks", []), ["task_id", "appearance_asset_key", "canonical_name", "costume_id", "base_lock_key", "status"], "appearance_tasks", issues)
        score -= _check_rows(stage_id, data.get("storyboard_frame_tasks", []), ["task_id", "frame_id", "sequence_index", "scene_ref_key", "appearance_asset_keys", "status"], "storyboard_frame_tasks", issues)
        dep = data.get("dependency_index", {}) if isinstance(data.get("dependency_index"), dict) else {}
        if not dep.get("frame_dependencies"):
            issues.append("dependency_index.frame_dependencies 不能为空")
            score -= 12
    elif stage_id == "07A":
        score -= _check_rows(stage_id, data.get("character_locks", []), ["lock_key", "canonical_name", "selected_image_path", "status", "revision"], "character_locks", issues)
    elif stage_id == "07B":
        score -= _check_rows(stage_id, data.get("appearances", []), ["appearance_asset_key", "canonical_name", "costume_id", "base_lock_key", "selected_image_path", "status"], "appearances", issues)
    elif stage_id == "07C":
        rows = data.get("reference_assets", [])
        if isinstance(rows, list) and not rows:
            # 有些纯人物近景章节可能没有道具，但通常至少有场景。这里只轻扣，不阻塞。
            issues.append("reference_assets 为空，请确认 06 frames 是否缺少场景/道具绑定")
            score -= 8
        else:
            score -= _check_rows(stage_id, rows, ["asset_kind", "asset_key", "selected_image_path", "status"], "reference_assets", issues)
    elif stage_id == "07D":
        score -= _check_rows(stage_id, data.get("images", []), ["frame_id", "sequence_index", "image_path", "status", "reference_images"], "images", issues)
        manifest = data.get("image_manifest", {}) if isinstance(data.get("image_manifest"), dict) else {}
        if not isinstance(manifest.get("images", []), list) or not manifest.get("images"):
            issues.append("image_manifest.images 不能为空")
            score -= 20
    elif stage_id == "07E":
        report = data.get("quality_report", {}) if isinstance(data.get("quality_report"), dict) else {}
        if report.get("needs_retry") and not data.get("retry_plan"):
            issues.append("07E needs_retry=true 时必须有 retry_plan")
            score -= 15
        registry = data.get("asset_image_registry", {}) if isinstance(data.get("asset_image_registry"), dict) else {}
        if not isinstance(registry.get("entries", []), list):
            issues.append("asset_image_registry.entries 必须为数组")
            score -= 15

    summary = data.get("execution_summary", {}) if isinstance(data.get("execution_summary"), dict) else {}
    if summary.get("failed", 0):
        issues.append(f"存在执行失败任务：{summary.get('failed')}")
        score -= 20
    score = max(0, min(100, score))
    return {
        "score": score,
        "passed": score >= THRESHOLD,
        "issues": issues,
        "revision_instructions": [f"请修复：{issue}" for issue in issues],
    }
