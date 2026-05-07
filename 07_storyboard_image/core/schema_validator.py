from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "execution_mode", "source",
    "plan", "dependency_index", "asset_image_registry", "character_lock_manifest",
    "appearance_manifest", "reference_asset_manifest", "image_manifest", "images",
    "retry_plan", "quality_report", "schema_validation",
]
REQUIRED_IMAGE_FIELDS = [
    "frame_id", "sequence_index", "source_frame_id", "image_path", "status", "execution_mode",
    "scene", "characters", "props", "reference_images", "prompt_summary",
]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")

    plan = data.get("plan", {}) if isinstance(data.get("plan"), dict) else {}
    frame_tasks = _list(plan.get("storyboard_frame_tasks") or data.get("frame_image_tasks"))
    if not frame_tasks:
        issues.append("plan.storyboard_frame_tasks 为空或不是数组")
    task_frame_ids = {str(task.get("frame_id")) for task in frame_tasks if isinstance(task, dict) and task.get("frame_id")}

    dep = data.get("dependency_index", {}) if isinstance(data.get("dependency_index"), dict) else {}
    if not isinstance(dep.get("frame_dependencies", {}), dict) or not dep.get("frame_dependencies"):
        issues.append("dependency_index.frame_dependencies 不能为空")

    character_locks = _list((data.get("character_lock_manifest", {}) or {}).get("character_locks") if isinstance(data.get("character_lock_manifest"), dict) else [])
    appearances = _list((data.get("appearance_manifest", {}) or {}).get("appearances") if isinstance(data.get("appearance_manifest"), dict) else [])
    app_keys = {str(item.get("appearance_asset_key")) for item in appearances if isinstance(item, dict) and item.get("appearance_asset_key")}
    lock_keys = {str(item.get("lock_key")) for item in character_locks if isinstance(item, dict) and item.get("lock_key")}
    for item in appearances:
        if isinstance(item, dict) and item.get("base_lock_key") and lock_keys and str(item.get("base_lock_key")) not in lock_keys:
            issues.append(f"appearance 引用了不存在的 base_lock_key：{item.get('appearance_asset_key')} -> {item.get('base_lock_key')}")

    reference_manifest = data.get("reference_asset_manifest", {}) if isinstance(data.get("reference_asset_manifest"), dict) else {}
    scene_keys = {str(item.get("scene_key")) for item in _list(reference_manifest.get("scene_assets")) if isinstance(item, dict) and item.get("scene_key")}
    prop_keys = {str(item.get("prop_key")) for item in _list(reference_manifest.get("prop_assets")) if isinstance(item, dict) and item.get("prop_key")}

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
        for app_key in image.get("appearance_asset_keys", []) or []:
            if app_keys and str(app_key) not in app_keys:
                issues.append(f"分镜 {fid} 引用了不存在的 appearance_asset_key：{app_key}")
        scene_key = str(image.get("scene_ref_key", ""))
        if scene_key and scene_keys and scene_key not in scene_keys:
            issues.append(f"分镜 {fid} 引用了不存在的 scene_ref_key：{scene_key}")
        for prop_key in image.get("prop_ref_keys", []) or []:
            if prop_keys and str(prop_key) not in prop_keys:
                issues.append(f"分镜 {fid} 引用了不存在的 prop_ref_key：{prop_key}")
    if task_frame_ids and image_frame_ids and task_frame_ids != image_frame_ids:
        issues.append(f"plan.storyboard_frame_tasks 与 images frame_id 不一致：tasks={sorted(task_frame_ids)} images={sorted(image_frame_ids)}")
    if seq_values and seq_values != set(range(1, len(seq_values) + 1)):
        issues.append("images.sequence_index 必须从 1 连续递增")

    registry = data.get("asset_image_registry", {}) if isinstance(data.get("asset_image_registry"), dict) else {}
    if not isinstance(registry.get("entries", []), list):
        issues.append("asset_image_registry.entries 必须为数组")

    report = data.get("quality_report", {})
    if not isinstance(report, dict):
        issues.append("quality_report 必须为对象")
    else:
        retry_plan = report.get("retry_plan") or data.get("retry_plan") or {}
        if report.get("needs_retry") and not retry_plan:
            issues.append("quality_report.needs_retry=true 时必须输出 retry_plan")
    if data.get("execution_mode") not in {"dry_run", "execute", "comfyui", "real"}:
        issues.append("execution_mode 必须为 dry_run/execute/comfyui/real")
    return {"passed": not issues, "issues": issues}
