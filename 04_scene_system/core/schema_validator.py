from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "scenes", "scene_alias_index",
    "scene_script_usage", "quality_report", "schema_validation"
]
REQUIRED_SCENE_FIELDS = [
    "scene_id", "canonical_scene_name", "aliases", "scene_type", "time_period",
    "lighting", "weather", "atmosphere", "layout", "key_visual_elements",
    "continuity_rules", "source_evidence", "usage_in_script",
    "asset_level", "needs_reference_image", "reference_image_plan", "parent_scene"
]
VALID_ASSET_LEVELS = {"main_scene", "sub_scene", "temporary", "background"}


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        issues.append("scenes 为空或不是数组")
        scenes = []
    ids: set[str] = set()
    names: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for idx, item in enumerate(scenes):
        if not isinstance(item, dict):
            issues.append(f"scenes[{idx}] 不是对象")
            continue
        for field in REQUIRED_SCENE_FIELDS:
            if item.get(field) in (None, "", [], {}):
                issues.append(f"场景 {item.get('canonical_scene_name', idx)} 缺少必要字段：{field}")
        if "prompt" in item or "image_prompt" in item or "desc_prompt" in item:
            issues.append(f"场景含图像提示词字段，越界：{item.get('canonical_scene_name', idx)}")
        sid = str(item.get("scene_id", "")).strip()
        name = str(item.get("canonical_scene_name", "")).strip()
        if sid in ids:
            issues.append(f"scene_id 重复：{sid}")
        if sid:
            ids.add(sid)
        if name in names:
            issues.append(f"canonical_scene_name 重复：{name}")
        if name:
            names.add(name)
        asset_level = item.get("asset_level")
        if asset_level not in VALID_ASSET_LEVELS:
            issues.append(f"场景 asset_level 非法：{name or sid} -> {asset_level}")
        if asset_level == "main_scene" and item.get("needs_reference_image") is not True:
            issues.append(f"主场景必须 needs_reference_image=true：{name or sid}")
        if asset_level == "sub_scene" and not str(item.get("parent_scene", "")).strip():
            issues.append(f"子场景必须绑定 parent_scene：{name or sid}")
        plan = item.get("reference_image_plan")
        if isinstance(plan, dict):
            images = plan.get("recommended_images", [])
            if asset_level == "main_scene" and "wide_establishing_view" not in images:
                issues.append(f"主场景参考图计划必须包含 wide_establishing_view：{name or sid}")
        for alias in item.get("aliases", []) or []:
            alias_key = str(alias).strip()
            if not alias_key:
                continue
            prev = aliases_seen.get(alias_key)
            if prev and prev != name:
                issues.append(f"同一场景别名被多个场景占用：{alias_key} -> {prev} / {name}")
            aliases_seen[alias_key] = name
        if not isinstance(item.get("source_evidence"), list) or not item.get("source_evidence"):
            issues.append(f"场景缺少证据链：{name or sid}")
        if not isinstance(item.get("usage_in_script"), list):
            issues.append(f"usage_in_script 必须为数组：{name or sid}")
    return {"passed": not issues, "issues": issues}
