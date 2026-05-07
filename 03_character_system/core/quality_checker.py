from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "03A": ["character_alias_groups", "merge_policy", "risk_report"],
    "03B": ["characters"],
    "03C": ["script_usage_map", "coverage_report"],
    "03D": ["quality_report", "evidence_index", "revision_plan"],
}
REQUIRED_PRESENT_BY_STAGE = {
    "03E": ["review_report", "downstream_readiness_for_06", "main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset"],
}

REQUIRED_CHARACTER_FIELDS = [
    "character_id", "canonical_name", "aliases", "gender", "age_range", "identity",
    "appearance", "costume", "temperament", "role_function", "source_evidence", "usage_in_script",
    "asset_level", "needs_fixed_face", "reference_image_priority", "reference_image_plan",
    "asset_importance_score", "importance_reason", "source_understanding_basis"
]

VALID_ASSET_LEVELS = {"main", "supporting", "extra_group", "mentioned_only"}
VALID_REFERENCE_PRIORITIES = {"required", "optional", "not_needed"}
VALID_RETRY_STAGES = {"03A", "03B", "03C", "03D"}


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _check_review_report(stage_id: str, data: dict[str, Any], issues: list[str]) -> int:
    score_delta = 0
    report = data.get("review_report", {}) if isinstance(data.get("review_report"), dict) else {}
    if not report:
        issues.append(f"{stage_id} 缺少 review_report")
        return -25
    required = ["score", "passed", "needs_retry", "retry_stages", "revision_instructions", "downstream_readiness", "missing_asset_check", "merge_error_check", "level_error_check", "reference_image_strategy_check"]
    for field in required:
        if field not in report:
            issues.append(f"{stage_id}.review_report 缺少字段：{field}")
            score_delta -= 5
    retry_stages = report.get("retry_stages", []) or []
    for retry_stage in retry_stages:
        if retry_stage not in VALID_RETRY_STAGES:
            issues.append(f"{stage_id}.review_report.retry_stages 非法：{retry_stage}")
            score_delta -= 10
    if report.get("needs_retry") and not report.get("revision_instructions"):
        issues.append(f"{stage_id} 需要重跑但没有 revision_instructions")
        score_delta -= 15
    readiness = data.get("downstream_readiness_for_06", {}) if isinstance(data.get("downstream_readiness_for_06"), dict) else {}
    if not readiness:
        issues.append(f"{stage_id} 缺少 downstream_readiness_for_06")
        score_delta -= 15
    else:
        for field in ["ready", "blocking_issues", "main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset"]:
            if field not in readiness:
                issues.append(f"downstream_readiness_for_06 缺少字段：{field}")
                score_delta -= 4
    for list_field in ["main_assets_for_06", "optional_assets_for_06", "do_not_reference_as_main_asset"]:
        if list_field in data and not isinstance(data.get(list_field), list):
            issues.append(f"{list_field} 必须为数组")
            score_delta -= 8
    return score_delta


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18
    for field in REQUIRED_PRESENT_BY_STAGE.get(stage_id, []):
        if field not in data:
            issues.append(f"缺少字段：{field}")
            score -= 18

    if stage_id == "03B":
        for idx, item in enumerate(data.get("characters", []) or []):
            if not isinstance(item, dict):
                issues.append(f"characters[{idx}] 不是对象")
                score -= 10
                continue
            for field in REQUIRED_CHARACTER_FIELDS:
                if not _non_empty(item.get(field)):
                    issues.append(f"角色 {item.get('canonical_name', idx)} 缺少字段：{field}")
                    score -= 5
            name = str(item.get("canonical_name", ""))
            if any(prefix in name for prefix in ["年轻", "少年", "中年", "老年", "年老"]):
                issues.append(f"疑似按年龄段拆分角色：{name}")
                score -= 20
            if item.get("asset_level") not in VALID_ASSET_LEVELS:
                issues.append(f"角色 {name or idx} asset_level 非法：{item.get('asset_level')}")
                score -= 10
            if item.get("reference_image_priority") not in VALID_REFERENCE_PRIORITIES:
                issues.append(f"角色 {name or idx} reference_image_priority 非法：{item.get('reference_image_priority')}")
                score -= 10
            if item.get("asset_level") in {"main", "supporting"} and item.get("needs_fixed_face") is not True:
                issues.append(f"主/配角必须 needs_fixed_face=true：{name or idx}")
                score -= 10
            if item.get("asset_level") in {"extra_group", "mentioned_only"} and item.get("reference_image_priority") == "required":
                issues.append(f"龙套/仅提及角色不应强制参考图：{name or idx}")
                score -= 8
            importance = item.get("asset_importance_score")
            if not isinstance(importance, (int, float)) or importance < 0 or importance > 100:
                issues.append(f"角色 {name or idx} asset_importance_score 必须为 0-100")
                score -= 8
    if stage_id == "03D":
        qr = data.get("quality_report", {}) if isinstance(data.get("quality_report"), dict) else {}
        if qr.get("needs_retry") and not qr.get("retry_stages"):
            issues.append("03D 要求重跑但未给 retry_stages")
            score -= 20
    if stage_id == "03E":
        score += _check_review_report(stage_id, data, issues)

    score = max(0, min(100, score))
    revision_instructions = [f"请修复：{issue}" for issue in issues]
    return {"score": score, "passed": score >= THRESHOLD, "issues": issues, "revision_instructions": revision_instructions}


def build_revision_payload(stage_id: str, original_payload: dict[str, Any], previous_output: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "original_payload": original_payload,
        "previous_output": previous_output,
        "revision_instructions": quality.get("revision_instructions", []),
        "task": f"重跑 {stage_id}。必须保留完整 JSON 字段，只修复评分指出的问题。",
    }
