from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "execution_mode", "source",
    "reference_asset_tasks", "frame_image_tasks", "execution_results", "images",
    "missing_references", "quality_report", "schema_validation",
]
REQUIRED_IMAGE_FIELDS = [
    "frame_id", "sequence_index", "source_frame_id", "image_path", "status", "execution_mode",
    "scene", "characters", "props", "reference_images", "prompt_summary",
]


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")

    tasks = data.get("frame_image_tasks", [])
    if not isinstance(tasks, list) or not tasks:
        issues.append("frame_image_tasks 为空或不是数组")
        tasks = []
    task_frame_ids = {str(task.get("frame_id")) for task in tasks if isinstance(task, dict) and task.get("frame_id")}

    results = data.get("execution_results", [])
    if not isinstance(results, list) or not results:
        issues.append("execution_results 为空或不是数组")
        results = []
    result_frame_ids = {str(result.get("frame_id")) for result in results if isinstance(result, dict) and result.get("frame_id")}
    if task_frame_ids and result_frame_ids and task_frame_ids != result_frame_ids:
        issues.append(f"frame_image_tasks 与 execution_results frame_id 不一致：tasks={sorted(task_frame_ids)} results={sorted(result_frame_ids)}")

    images = data.get("images", [])
    if not isinstance(images, list) or not images:
        issues.append("images 为空或不是数组")
        images = []
    image_frame_ids: set[str] = set()
    seq_values: set[int] = set()
    for idx, image in enumerate(images):
        if not isinstance(image, dict):
            issues.append(f"images[{idx}] 不是对象")
            continue
        for field in REQUIRED_IMAGE_FIELDS:
            if field not in image:
                issues.append(f"images[{idx}] 缺少字段：{field}")
        fid = str(image.get("frame_id", "")).strip()
        if not fid:
            issues.append(f"images[{idx}] 缺少 frame_id")
        elif fid in image_frame_ids:
            issues.append(f"images frame_id 重复：{fid}")
        else:
            image_frame_ids.add(fid)
        seq = image.get("sequence_index")
        if not isinstance(seq, int) or seq < 1:
            issues.append(f"images[{idx}].sequence_index 必须为正整数")
        elif seq in seq_values:
            issues.append(f"images sequence_index 重复：{seq}")
        else:
            seq_values.add(seq)
        if not image.get("image_path"):
            issues.append(f"images[{idx}] image_path 不能为空")
        if not isinstance(image.get("reference_images", []), list):
            issues.append(f"images[{idx}].reference_images 必须为数组")
    if task_frame_ids and image_frame_ids and task_frame_ids != image_frame_ids:
        issues.append(f"frame_image_tasks 与 images frame_id 不一致：tasks={sorted(task_frame_ids)} images={sorted(image_frame_ids)}")
    if seq_values and seq_values != set(range(1, len(seq_values) + 1)):
        issues.append("images.sequence_index 必须从 1 连续递增")

    report = data.get("quality_report", {})
    if not isinstance(report, dict):
        issues.append("quality_report 必须为对象")
    else:
        if report.get("needs_retry") and not report.get("retry_frames"):
            issues.append("quality_report.needs_retry=true 时必须输出 retry_frames")
    if data.get("execution_mode") not in {"dry_run", "execute", "comfyui", "real"}:
        issues.append("execution_mode 必须为 dry_run/execute/comfyui/real")
    return {"passed": not issues, "issues": issues}
