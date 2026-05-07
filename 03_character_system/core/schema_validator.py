from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "characters", "alias_index",
    "character_script_usage", "asset_review_report", "downstream_readiness_for_06",
    "main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset",
    "quality_report"
]
REQUIRED_CHARACTER_FIELDS = [
    "character_id", "canonical_name", "aliases", "gender", "age_range", "identity",
    "appearance", "costume", "default_costume_id", "costume_variants", "temperament", "role_function", "source_evidence", "usage_in_script",
    "asset_level", "needs_fixed_face", "reference_image_priority", "reference_image_plan",
    "asset_importance_score", "importance_reason", "source_understanding_basis"
]
REQUIRED_COSTUME_FIELDS = [
    "costume_id", "costume_name", "stage_label", "is_default", "appearance_state",
    "hair_style", "headwear", "upper_garment", "lower_garment", "footwear",
    "outerwear", "color_palette", "integrated_wearable_props", "script_usage_refs",
    "continuity_notes", "reference_image_priority"
]
VALID_ASSET_LEVELS = {"main", "supporting", "extra_group", "mentioned_only"}
VALID_REFERENCE_PRIORITIES = {"required", "optional", "not_needed"}


def _validate_costumes(item: dict[str, Any], issues: list[str]) -> None:
    name = str(item.get("canonical_name", "")).strip()
    asset_level = item.get("asset_level")
    variants = item.get("costume_variants")
    default_id = str(item.get("default_costume_id", "")).strip()
    if asset_level not in {"main", "supporting"}:
        return
    if not isinstance(variants, list) or not variants:
        issues.append(f"主/配角必须包含 costume_variants：{name}")
        return
    ids: set[str] = set()
    default_count = 0
    for idx, variant in enumerate(variants):
        if not isinstance(variant, dict):
            issues.append(f"角色 {name} costume_variants[{idx}] 不是对象")
            continue
        for field in REQUIRED_COSTUME_FIELDS:
            if variant.get(field) in (None, "", []):
                issues.append(f"角色 {name} 服装版本缺少必要字段：{field}")
        cid = str(variant.get("costume_id", "")).strip()
        if cid in ids:
            issues.append(f"角色 {name} costume_id 重复：{cid}")
        if cid:
            ids.add(cid)
        if variant.get("is_default") is True:
            default_count += 1
        if not isinstance(variant.get("integrated_wearable_props", []), list):
            issues.append(f"角色 {name} integrated_wearable_props 必须为数组")
        if not isinstance(variant.get("script_usage_refs", []), list):
            issues.append(f"角色 {name} script_usage_refs 必须为数组")
        if variant.get("reference_image_priority") not in VALID_REFERENCE_PRIORITIES:
            issues.append(f"角色 {name} 服装 reference_image_priority 非法：{variant.get('reference_image_priority')}")
    if not default_id:
        issues.append(f"角色 {name} 缺少 default_costume_id")
    elif default_id not in ids:
        issues.append(f"角色 {name} default_costume_id 不存在于 costume_variants：{default_id}")
    if default_count != 1:
        issues.append(f"角色 {name} costume_variants 必须且只能有一个 is_default=true")


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    for list_field in ["main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset"]:
        if list_field in data and not isinstance(data.get(list_field), list):
            issues.append(f"{list_field} 必须为数组。")
    characters = data.get("characters", [])
    if not isinstance(characters, list) or not characters:
        issues.append("characters 为空或不是数组")
        characters = []
    ids: set[str] = set()
    names: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for idx, item in enumerate(characters):
        if not isinstance(item, dict):
            issues.append(f"characters[{idx}] 不是对象")
            continue
        for field in REQUIRED_CHARACTER_FIELDS:
            if item.get(field) in (None, "", [], {}):
                issues.append(f"角色 {item.get('canonical_name', idx)} 缺少必要字段：{field}")
        cid = str(item.get("character_id", "")).strip()
        name = str(item.get("canonical_name", "")).strip()
        if cid in ids:
            issues.append(f"character_id 重复：{cid}")
        if cid:
            ids.add(cid)
        if name in names:
            issues.append(f"canonical_name 重复：{name}")
        if name:
            names.add(name)
        if any(prefix in name for prefix in ["年轻", "少年", "中年", "老年", "年老"]):
            issues.append(f"禁止按年龄段拆角色：{name}")
        importance = item.get("asset_importance_score")
        if not isinstance(importance, (int, float)) or importance < 0 or importance > 100:
            issues.append(f"asset_importance_score 必须为 0-100：{name or cid}")
        if not isinstance(item.get("source_understanding_basis"), list) or not item.get("source_understanding_basis"):
            issues.append(f"source_understanding_basis 必须引用 01 理解依据：{name or cid}")
        asset_level = item.get("asset_level")
        ref_priority = item.get("reference_image_priority")
        if asset_level not in VALID_ASSET_LEVELS:
            issues.append(f"角色 asset_level 非法：{name or cid} -> {asset_level}")
        if ref_priority not in VALID_REFERENCE_PRIORITIES:
            issues.append(f"角色 reference_image_priority 非法：{name or cid} -> {ref_priority}")
        if asset_level in {"main", "supporting"} and item.get("needs_fixed_face") is not True:
            issues.append(f"主/配角必须 needs_fixed_face=true：{name or cid}")
        if asset_level in {"extra_group", "mentioned_only"} and ref_priority == "required":
            issues.append(f"龙套/仅提及角色不应强制参考图：{name or cid}")
        plan = item.get("reference_image_plan")
        if isinstance(plan, dict):
            if asset_level == "main" and "front_face_half_body" not in plan.get("recommended_images", []):
                issues.append(f"核心角色参考图计划必须包含 front_face_half_body：{name or cid}")
        _validate_costumes(item, issues)
        for alias in item.get("aliases", []) or []:
            alias_key = str(alias).strip()
            if not alias_key:
                continue
            prev = aliases_seen.get(alias_key)
            if prev and prev != name:
                issues.append(f"同一别名被多个角色占用：{alias_key} -> {prev} / {name}")
            aliases_seen[alias_key] = name
        if not isinstance(item.get("source_evidence"), list) or not item.get("source_evidence"):
            issues.append(f"角色缺少证据链：{name or cid}")
        if not isinstance(item.get("usage_in_script"), list):
            issues.append(f"usage_in_script 必须为数组：{name or cid}")
    review = data.get("asset_review_report", {})
    if not isinstance(review, dict) or not review:
        issues.append("asset_review_report 为空或不是对象")
    readiness = data.get("downstream_readiness_for_06", {})
    if not isinstance(readiness, dict) or "ready" not in readiness:
        issues.append("downstream_readiness_for_06 必须包含 ready 字段")
    return {"passed": not issues, "issues": issues}
