from __future__ import annotations

from typing import Any


STAGE_THRESHOLDS = {
    "02A": 85,
    "02B": 85,
    "02C": 90,
    "02D": 85,
    "02E": 90,
}

REQUIRED_KEYS = {
    "02A": ["adaptation_blueprint", "coverage_plan", "tone_plan", "compression_guardrails"],
    "02B": ["script_structure", "scene_beats", "event_coverage_map", "retention_design"],
    "02C": ["script", "segments", "script_text"],
    "02D": ["production_annotations", "audio_cues", "storyboard_hints", "risk_report"],
    "02E": ["quality_report", "evidence_index", "warnings", "revision_plan"],
}


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_KEYS.get(stage_id, []) if key not in data]
    score = 100 - len(missing) * 15
    issues: list[str] = []
    suggestions: list[str] = []

    if missing:
        issues.append(f"缺少必要字段：{', '.join(missing)}")
        suggestions.append("补齐缺失字段，并保持字段名与 02 schema 完全一致。")

    if data.get("status") == "scaffold":
        score = min(score, 50)
        issues.append("当前仍是 scaffold 占位输出。")
        suggestions.append("调用真实 LLM 生成本阶段内容，避免只返回占位文本。")

    if stage_id == "02A":
        score, issues, suggestions = _evaluate_blueprint(data, score, issues, suggestions)
    elif stage_id == "02B":
        score, issues, suggestions = _evaluate_structure(data, score, issues, suggestions)
    elif stage_id == "02C":
        score, issues, suggestions = _evaluate_script(data, score, issues, suggestions)
    elif stage_id == "02D":
        score, issues, suggestions = _evaluate_annotations(data, score, issues, suggestions)
    elif stage_id == "02E":
        score, issues, suggestions = _evaluate_final_check(data, score, issues, suggestions)

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


def _evaluate_blueprint(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    plan = data.get("coverage_plan") or []
    if not isinstance(plan, list) or not plan:
        score -= 20
        issues.append("coverage_plan 为空，无法保证关键事件不遗漏。")
        suggestions.append("按 01 的 events / high_retention_segments 逐项列出改编覆盖计划。")
    guardrails = data.get("compression_guardrails") or {}
    if not guardrails:
        score -= 15
        issues.append("compression_guardrails 为空，容易把 3000 字内容压成过短剧本。")
        suggestions.append("明确不得过度压缩、不得把多个关键事件合并成一句话的规则。")
    return score, issues, suggestions


def _evaluate_structure(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    beats = data.get("scene_beats") or []
    if not isinstance(beats, list) or len(beats) < 2:
        score -= 25
        issues.append("scene_beats 数量过少，剧本结构可能压缩过狠。")
        suggestions.append("至少按开场压迫、冲突升级、转折/反杀、余韵拆成多个 beat。")
    coverage = data.get("event_coverage_map") or []
    if not isinstance(coverage, list) or not coverage:
        score -= 20
        issues.append("event_coverage_map 为空，无法验证事件覆盖。")
        suggestions.append("为每个使用到的 source_event_id 标记对应 scene_beat_id。")
    return score, issues, suggestions


def _evaluate_script(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    segments = data.get("segments") or []
    if not isinstance(segments, list) or not segments:
        score -= 35
        issues.append("segments 为空，未生成正式剧本段落。")
        suggestions.append("生成包含 OS、对白、动作、留白的 segments 数组。")
        return score, issues, suggestions

    types = {str(item.get("type")) for item in segments if isinstance(item, dict)}
    if "os" not in types:
        score -= 15
        issues.append("剧本缺少 OS 段落。")
        suggestions.append("补充【OS】旁白/心理独白，用于承接信息和情绪。")
    if "dialogue" not in types:
        score -= 20
        issues.append("剧本缺少对白段落。")
        suggestions.append("补充角色对白，保留原文关键冲突、羞辱、逼问、反杀信息。")
    if "blank" not in types:
        score -= 10
        issues.append("剧本缺少留白段落。")
        suggestions.append("补充【留白】节奏停顿，给音频和画面呼吸空间。")

    for item in segments:
        if not isinstance(item, dict):
            continue
        if not item.get("segment_id"):
            score -= 5
            issues.append("存在 segment 缺少 segment_id。")
            suggestions.append("每个 segment 必须有稳定 segment_id。")
            break
    return score, issues, suggestions


def _evaluate_annotations(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    if not data.get("audio_cues"):
        score -= 15
        issues.append("audio_cues 为空，08 配音难以使用语气/停顿信息。")
        suggestions.append("为 OS 和 dialogue 段落补充 speaker、emotion、pace、pause_hint。")
    if not data.get("storyboard_hints"):
        score -= 15
        issues.append("storyboard_hints 为空，06 分镜难以抓画面动作锚点。")
        suggestions.append("为关键 segment 补充 visual_anchor、action_chain、shot_intent。")
    return score, issues, suggestions


def _evaluate_final_check(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    report = data.get("quality_report") or {}
    if isinstance(report, dict) and report.get("needs_retry"):
        score -= 25
        issues.append("02E 总检要求重跑阶段。")
        suggestions.append("按 quality_report.retry_stages 和 revision_instructions 从最早问题阶段重跑。")
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
