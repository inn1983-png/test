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


def _compact_text(text: str, head: int = 9000, tail: int = 3000) -> str:
    if len(text) <= head + tail + 200:
        return text
    return text[:head] + "\n...[中间原文已省略，用于避免本地模型重跑时上下文爆炸]...\n" + text[-tail:]


def _compact_original_input(stage_id: str, original_payload: dict[str, Any]) -> dict[str, Any]:
    if stage_id == "01A":
        text = str(original_payload.get("novel_text", ""))
        return {"novel_text": _compact_text(text), "note": "重跑阶段使用压缩原文。必须补齐缺失字段，不要复述原文。"}
    if stage_id == "01B":
        return {
            "base_split": original_payload.get("base_split", []),
            "instruction": original_payload.get("instruction", "保留 base_split，只补充标注。"),
        }
    if stage_id in {"01C", "01D", "01E"}:
        return {key: original_payload.get(key) for key in original_payload if key != "paragraphs"} | {
            "paragraphs_summary": "重跑时不回传完整 paragraphs，按 previous_output 和 revision_instructions 修复字段结构。"
        }
    if stage_id == "01F":
        return {"note": "01F 重跑只根据 quality_report 修复总检报告，不回传完整 stage_outputs。"}
    return original_payload


def _compact_previous_output(stage_id: str, previous: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in REQUIRED_KEYS.get(stage_id, []):
        value = previous.get(key)
        if isinstance(value, str):
            result[key] = _compact_text(value, 2000, 500)
        elif isinstance(value, list):
            result[key] = value[:30]
            if len(value) > 30:
                result[f"{key}_truncated_note"] = f"原数组 {len(value)} 项，重跑 payload 只保留前 30 项。"
        elif isinstance(value, dict):
            result[key] = value
        else:
            result[key] = value
    result["schema_version"] = previous.get("schema_version")
    result["stage"] = previous.get("stage")
    return result


def build_revision_payload(stage_id: str, original_payload: dict[str, Any], last_output: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "revise_previous_stage_output_compact",
        "stage_id": stage_id,
        "original_input_compact": _compact_original_input(stage_id, original_payload),
        "previous_output_compact": _compact_previous_output(stage_id, last_output or {}),
        "quality_report": {
            "score": quality.get("score"),
            "threshold": quality.get("threshold"),
            "issues": quality.get("issues", []),
            "revision_instructions": quality.get("revision_instructions", []),
        },
        "instruction": "请严格根据 quality_report.revision_instructions 修正 previous_output_compact。必须补齐本阶段必要字段，只输出修正后的完整 JSON 对象，不要输出解释。",
    }
