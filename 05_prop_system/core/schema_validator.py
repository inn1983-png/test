from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "props", "prop_alias_index",
    "prop_script_usage", "asset_review_report", "downstream_readiness_for_06",
    "main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset",
    "quality_report"
]
REQUIRED_PROP_FIELDS = [
    "prop_id", "canonical_prop_name", "aliases", "prop_type", "owner_character",
    "usage_function", "appearance", "material", "risk_notes", "source_evidence", "usage_in_script",
    "asset_level", "needs_reference_image", "reference_image_plan",
    "asset_importance_score", "importance_reason", "source_understanding_basis"
]
VALID_ASSET_LEVELS = {"key_prop", "action_prop", "background_object", "mentioned_only"}


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    for list_field in ["main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset"]:
        if list_field in data and not isinstance(data.get(list_field), list):
            issues.append(f"{list_field} 必须为数组。")
    props = data.get("props", [])
    if not isinstance(props, list) or not props:
        issues.append("props 为空或不是数组")
        props = []
    ids: set[str] = set()
    names: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for idx, item in enumerate(props):
        if not isinstance(item, dict):
            issues.append(f"props[{idx}] 不是对象")
            continue
        for field in REQUIRED_PROP_FIELDS:
            if item.get(field) in (None, "", [], {}):
                issues.append(f"道具 {item.get('canonical_prop_name', idx)} 缺少必要字段：{field}")
        if "prompt" in item or "image_prompt" in item or "desc_prompt" in item:
            issues.append(f"道具含图像提示词字段，越界：{item.get('canonical_prop_name', idx)}")
        pid = str(item.get("prop_id", "")).strip()
        name = str(item.get("canonical_prop_name", "")).strip()
        if pid in ids:
            issues.append(f"prop_id 重复：{pid}")
        if pid:
            ids.add(pid)
        if name in names:
            issues.append(f"canonical_prop_name 重复：{name}")
        if name:
            names.add(name)
        importance = item.get("asset_importance_score")
        if not isinstance(importance, (int, float)) or importance < 0 or importance > 100:
            issues.append(f"asset_importance_score 必须为 0-100：{name or pid}")
        if not isinstance(item.get("source_understanding_basis"), list) or not item.get("source_understanding_basis"):
            issues.append(f"source_understanding_basis 必须引用 01 理解依据：{name or pid}")
        asset_level = item.get("asset_level")
        if asset_level not in VALID_ASSET_LEVELS:
            issues.append(f"道具 asset_level 非法：{name or pid} -> {asset_level}")
        if asset_level == "key_prop" and item.get("needs_reference_image") is not True:
            issues.append(f"关键道具必须 needs_reference_image=true：{name or pid}")
        plan = item.get("reference_image_plan")
        if isinstance(plan, dict):
            images = plan.get("recommended_images", [])
            if asset_level == "key_prop" and "clean_front_view" not in images:
                issues.append(f"关键道具参考图计划必须包含 clean_front_view：{name or pid}")
        for alias in item.get("aliases", []) or []:
            alias_key = str(alias).strip()
            if not alias_key:
                continue
            prev = aliases_seen.get(alias_key)
            if prev and prev != name:
                issues.append(f"同一道具别名被多个道具占用：{alias_key} -> {prev} / {name}")
            aliases_seen[alias_key] = name
        if not isinstance(item.get("source_evidence"), list) or not item.get("source_evidence"):
            issues.append(f"道具缺少证据链：{name or pid}")
        if not isinstance(item.get("usage_in_script"), list):
            issues.append(f"usage_in_script 必须为数组：{name or pid}")
    review = data.get("asset_review_report", {})
    if not isinstance(review, dict) or not review:
        issues.append("asset_review_report 为空或不是对象")
    readiness = data.get("downstream_readiness_for_06", {})
    if not isinstance(readiness, dict) or "ready" not in readiness:
        issues.append("downstream_readiness_for_06 必须包含 ready 字段")
    return {"passed": not issues, "issues": issues}
