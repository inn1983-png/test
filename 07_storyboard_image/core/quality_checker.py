from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "07A": ["reference_asset_tasks", "missing_references", "asset_generation_policy"],
    "07B": ["frame_image_tasks", "prompt_style_policy", "negative_prompt_policy"],
    "07C": ["execution_results", "execution_summary"],
    "07D": ["image_manifest", "quality_report", "retry_plan"],
}


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18

    if stage_id == "07A":
        tasks = data.get("reference_asset_tasks", [])
        if not isinstance(tasks, list):
            issues.append("reference_asset_tasks 必须为数组")
            score -= 20
        for idx, task in enumerate(tasks or []):
            if not isinstance(task, dict):
                issues.append(f"reference_asset_tasks[{idx}] 不是对象")
                score -= 8
                continue
            for field in ["task_id", "asset_kind", "asset_key", "generation_stage", "source_reference"]:
                if field not in task:
                    issues.append(f"参考资产任务缺少字段：{field}")
                    score -= 4
    if stage_id == "07B":
        tasks = data.get("frame_image_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            issues.append("frame_image_tasks 不能为空")
            score -= 30
        for idx, task in enumerate(tasks or []):
            if not isinstance(task, dict):
                issues.append(f"frame_image_tasks[{idx}] 不是对象")
                score -= 8
                continue
            for field in ["task_id", "frame_id", "sequence_index", "positive_prompt", "negative_prompt", "reference_images", "output_basename"]:
                if field not in task:
                    issues.append(f"分镜图片任务缺少字段：{field}")
                    score -= 5
            if not isinstance(task.get("reference_images", []), list):
                issues.append(f"{task.get('frame_id', idx)} reference_images 必须为数组")
                score -= 8
    if stage_id == "07C":
        results = data.get("execution_results", [])
        if not isinstance(results, list) or not results:
            issues.append("execution_results 不能为空")
            score -= 30
        for idx, result in enumerate(results or []):
            if not isinstance(result, dict):
                issues.append(f"execution_results[{idx}] 不是对象")
                score -= 8
                continue
            for field in ["frame_id", "status", "execution_mode", "output_path"]:
                if field not in result:
                    issues.append(f"执行结果缺少字段：{field}")
                    score -= 5
    if stage_id == "07D":
        manifest = data.get("image_manifest", {})
        if not isinstance(manifest, dict):
            issues.append("image_manifest 必须为对象")
            score -= 25
        elif not isinstance(manifest.get("images", []), list) or not manifest.get("images"):
            issues.append("image_manifest.images 不能为空")
            score -= 25
        report = data.get("quality_report", {}) if isinstance(data.get("quality_report"), dict) else {}
        if report.get("needs_retry") and not report.get("retry_frames"):
            issues.append("quality_report.needs_retry=true 时必须给 retry_frames")
            score -= 15
    score = max(0, min(100, score))
    return {
        "score": score,
        "passed": score >= THRESHOLD,
        "issues": issues,
        "revision_instructions": [f"请修复：{issue}" for issue in issues],
    }
