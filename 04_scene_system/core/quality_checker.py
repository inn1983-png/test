from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "04A": ["scene_alias_groups", "merge_policy", "risk_report"],
    "04B": ["scenes"],
    "04C": ["script_usage_map", "coverage_report"],
    "04D": ["quality_report", "evidence_index", "revision_plan"],
}

REQUIRED_SCENE_FIELDS = [
    "scene_id", "canonical_scene_name", "aliases", "scene_type", "time_period",
    "lighting", "weather", "atmosphere", "layout", "key_visual_elements",
    "continuity_rules", "source_evidence", "usage_in_script"
]


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18

    if stage_id == "04B":
        for idx, item in enumerate(data.get("scenes", []) or []):
            if not isinstance(item, dict):
                issues.append(f"scenes[{idx}] 不是对象")
                score -= 10
                continue
            for field in REQUIRED_SCENE_FIELDS:
                if not _non_empty(item.get(field)):
                    issues.append(f"场景 {item.get('canonical_scene_name', idx)} 缺少字段：{field}")
                    score -= 5
            if "prompt" in item or "image_prompt" in item:
                issues.append(f"场景 {item.get('canonical_scene_name', idx)} 含图像提示词字段，越界")
                score -= 20
    if stage_id == "04D":
        qr = data.get("quality_report", {}) if isinstance(data.get("quality_report"), dict) else {}
        if qr.get("needs_retry") and not qr.get("retry_stages"):
            issues.append("04D 要求重跑但未给 retry_stages")
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
