from __future__ import annotations

from typing import Any


STAGE_THRESHOLDS = {
    "01A": 85,
    "01B": 90,
    "01C": 85,
    "01D": 95,
    "01E": 85,
    "01F": 90,
}

REQUIRED_KEYS = {
    "01A": ["story_understanding", "story_spine", "viewer_experience_plan", "information_reveal_plan", "adaptation_strategy", "misread_prevention"],
    "01B": ["chapters", "paragraphs", "timeline"],
    "01C": ["event_graph", "conflicts", "high_retention_segments", "scene_value_map", "character_arc_map"],
    "01D": ["candidate_extraction_policy", "candidate_characters", "candidate_scenes", "candidate_props", "asset_binding_hints", "visual_risk_report"],
    "01E": ["voice_line_candidates", "video_unit_candidates", "emotion_curve", "golden_lines", "confusion_risk_report"],
    "01F": ["evidence_index", "quality_report", "warnings", "chapter_memory_update"],
}


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_KEYS.get(stage_id, []) if key not in data]
    score = 100 - len(missing) * 15
    issues: list[str] = []
    suggestions: list[str] = []

    if missing:
        issues.append(f"缺少必要字段：{', '.join(missing)}")
        suggestions.append("补齐缺失字段，并保持字段名与 schema 完全一致。")

    if data.get("status") == "scaffold":
        score = min(score, 50)
        issues.append("当前仍是 scaffold 占位输出。")
        suggestions.append("调用真实 LLM 生成本阶段内容，避免只返回占位文本。")

    if stage_id == "01D":
        score, issues, suggestions = _evaluate_candidate_stage(data, score, issues, suggestions)
    elif stage_id == "01B":
        score, issues, suggestions = _evaluate_paragraph_stage(data, score, issues, suggestions)
    elif stage_id == "01A":
        score, issues, suggestions = _evaluate_story_stage(data, score, issues, suggestions)

    score = max(0, min(100, score))
    threshold = STAGE_THRESHOLDS.get(stage_id, 85)
    passed = score >= threshold and not missing

    return {
        "stage_id": stage_id,
        "score": score,
        "threshold": threshold,
        "passed": passed,
        "issues": issues,
        "revision_instructions": suggestions,
    }


def _evaluate_story_stage(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    su = data.get("story_understanding") or {}
    if not isinstance(su, dict) or not su.get("one_sentence_summary"):
        score -= 20
        issues.append("story_understanding 不完整，缺少一句话总结。")
        suggestions.append("重新通读全文，先用一句话说明故事到底讲什么。")
    if not data.get("story_spine"):
        score -= 20
        issues.append("story_spine 为空。")
        suggestions.append("补齐 opening_state / inciting_incident / rising_pressure / climax / ending_state。")
    return score, issues, suggestions


def _evaluate_paragraph_stage(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    paragraphs = data.get("paragraphs") or []
    if not paragraphs:
        score -= 30
        issues.append("paragraphs 为空，后续事件、候选、证据无法回链。")
        suggestions.append("必须按原文顺序切分段落，并为每段生成 paragraph_id。")
    return score, issues, suggestions


def _evaluate_candidate_stage(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    for key, label in [("candidate_characters", "角色"), ("candidate_scenes", "场景"), ("candidate_props", "道具")]:
        value = data.get(key)
        if not isinstance(value, list):
            score -= 20
            issues.append(f"{key} 不是数组。")
            suggestions.append(f"重新输出 {label} 候选数组。")
        elif len(value) == 0:
            score -= 15
            issues.append(f"{key} 为空，可能漏提取。")
            suggestions.append(f"按段落重新提取全部提到过的{label}，宁可多，不可漏。")
    return score, issues, suggestions


def build_revision_payload(stage_id: str, original_payload: dict[str, Any], last_output: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "revise_previous_stage_output",
        "stage_id": stage_id,
        "original_input": original_payload,
        "previous_output": last_output,
        "quality_report": quality,
        "instruction": "请严格根据 quality_report.revision_instructions 修正 previous_output，只输出修正后的 JSON 对象，不要输出解释。",
    }
