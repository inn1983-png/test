from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "05A": ["prop_alias_groups", "merge_policy", "risk_report"],
    "05B": ["props"],
    "05C": ["script_usage_map", "coverage_report"],
    "05D": ["quality_report", "evidence_index", "revision_plan"],
}

REQUIRED_PROP_FIELDS = [
    "prop_id", "canonical_prop_name", "aliases", "prop_type", "owner_character",
    "usage_function", "appearance", "material", "risk_notes", "source_evidence", "usage_in_script",
    "asset_level", "needs_reference_image", "reference_image_plan"
]

VALID_ASSET_LEVELS = {"key_prop", "action_prop", "background_object", "mentioned_only"}


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18

    if stage_id == "05B":
        for idx, item in enumerate(data.get("props", []) or []):
            if not isinstance(item, dict):
                issues.append(f"props[{idx}] 不是对象")
                score -= 10
                continue
            for field in REQUIRED_PROP_FIELDS:
                if not _non_empty(item.get(field)):
                    issues.append(f"道具 {item.get('canonical_prop_name', idx)} 缺少字段：{field}")
                    score -= 5
            if "prompt" in item or "image_prompt" in item:
                issues.append(f"道具 {item.get('canonical_prop_name', idx)} 含图像提示词字段，越界")
                score -= 20
            name = str(item.get("canonical_prop_name", idx))
            if item.get("asset_level") not in VALID_ASSET_LEVELS:
                issues.append(f"道具 {name} asset_level 非法：{item.get('asset_level')}")
                score -= 10
            if item.get("asset_level") == "key_prop" and item.get("needs_reference_image") is not True:
                issues.append(f"关键道具必须 needs_reference_image=true：{name}")
                score -= 10
            if item.get("asset_level") in {"background_object", "mentioned_only"} and item.get("needs_reference_image") is True:
                issues.append(f"背景/仅提及道具不建议强制参考图：{name}")
                score -= 6
    if stage_id == "05D":
        qr = data.get("quality_report", {}) if isinstance(data.get("quality_report"), dict) else {}
        if qr.get("needs_retry") and not qr.get("retry_stages"):
            issues.append("05D 要求重跑但未给 retry_stages")
            score -= 20

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
