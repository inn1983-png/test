from __future__ import annotations

from typing import Any


TOP_LEVEL_REQUIRED = [
    "schema_version",
    "module",
    "status",
    "stage_mode",
    "stage_status",
    "source",
    "script_id",
    "title",
    "format",
    "adaptation_blueprint",
    "length_strategy",
    "script_structure",
    "scene_beats",
    "voice_line_plan",
    "script_video_unit_candidates",
    "segments",
    "script_text",
    "source_line_usage",
    "character_name_usage",
    "production_annotations",
    "audio_cues",
    "visual_dramatic_units",
    "storyboard_hints",
    "quality_report",
]

ALLOWED_SEGMENT_TYPES = {"os", "dialogue", "blank", "action", "emotion"}
ALLOWED_VOICE_LINE_TYPES = {"N", "D", "M", "S"}


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    missing = [key for key in TOP_LEVEL_REQUIRED if key not in data]
    if missing:
        issues.append(f"最终 script.json 缺少顶层字段：{', '.join(missing)}")

    voice_lines = data.get("voice_line_plan", []) or []
    voice_line_ids = _validate_voice_line_plan(voice_lines, issues)

    segments = data.get("segments", []) or []
    if not isinstance(segments, list) or not segments:
        issues.append("segments 为空。")
        segment_ids: set[str] = set()
    else:
        segment_ids = _validate_segments(segments, voice_line_ids, issues)

    audio_cues = data.get("audio_cues", []) or []
    storyboard_hints = data.get("storyboard_hints", []) or []
    visual_units = data.get("visual_dramatic_units", []) or []
    video_units = data.get("script_video_unit_candidates", []) or []

    _validate_refs(audio_cues, segment_ids, voice_line_ids, "audio_cues", issues)
    _validate_refs(storyboard_hints, segment_ids, voice_line_ids, "storyboard_hints", issues)
    _validate_refs(visual_units, segment_ids, voice_line_ids, "visual_dramatic_units", issues)
    _validate_video_units(video_units, voice_line_ids, issues)

    event_coverage = data.get("event_coverage_map", []) or []
    if not event_coverage:
        issues.append("event_coverage_map 为空，无法确认 01 关键事件是否被剧本覆盖。")

    text = data.get("script_text", "")
    if not isinstance(text, str) or not text.strip():
        issues.append("script_text 为空。")

    source_line_usage = data.get("source_line_usage", []) or []
    if not isinstance(source_line_usage, list) or not source_line_usage:
        issues.append("source_line_usage 为空，无法确认原文关键句是否被继承。")

    character_name_usage = data.get("character_name_usage", []) or []
    if not isinstance(character_name_usage, list) or not character_name_usage:
        issues.append("character_name_usage 为空，无法检查角色称呼一致性。")

    return {
        "passed": not issues,
        "issues": issues,
        "hard_rule_count": len(issues),
    }


def _validate_voice_line_plan(items: list[dict[str, Any]], issues: list[str]) -> set[str]:
    voice_line_ids: set[str] = set()
    if not isinstance(items, list) or not items:
        issues.append("voice_line_plan 为空。")
        return voice_line_ids

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            issues.append(f"voice_line_plan[{index}] 不是对象。")
            continue
        line_id = item.get("voice_line_id")
        if not line_id:
            issues.append(f"voice_line_plan[{index}] 缺少 voice_line_id。")
        elif str(line_id) in voice_line_ids:
            issues.append(f"voice_line_id 重复：{line_id}")
        else:
            voice_line_ids.add(str(line_id))

        line_type = item.get("voice_line_type")
        if line_type not in ALLOWED_VOICE_LINE_TYPES:
            issues.append(f"voice_line {line_id} 类型非法：{line_type}")
        if line_type == "D" and not item.get("speaker"):
            issues.append(f"D 类型 voice_line {line_id} 缺少 speaker。")
        if line_type in {"N", "D", "M"} and not item.get("tts_text"):
            issues.append(f"voice_line {line_id} 缺少 tts_text。")
        duration = item.get("estimated_duration_sec")
        if isinstance(duration, (int, float)) and duration > 12:
            issues.append(f"voice_line {line_id} estimated_duration_sec 超过 12 秒：{duration}")
    return voice_line_ids


def _validate_segments(segments: list[dict[str, Any]], voice_line_ids: set[str], issues: list[str]) -> set[str]:
    segment_ids: set[str] = set()
    for index, item in enumerate(segments, start=1):
        if not isinstance(item, dict):
            issues.append(f"segments[{index}] 不是对象。")
            continue
        sid = item.get("segment_id")
        if not sid:
            issues.append(f"segments[{index}] 缺少 segment_id。")
        elif str(sid) in segment_ids:
            issues.append(f"segment_id 重复：{sid}")
        else:
            segment_ids.add(str(sid))
        stype = item.get("type")
        if stype not in ALLOWED_SEGMENT_TYPES:
            issues.append(f"segment {sid} type 非法：{stype}")
        if stype in {"os", "dialogue", "action", "emotion"} and not item.get("text"):
            issues.append(f"segment {sid} 缺少 text。")
        if stype == "dialogue" and not item.get("speaker"):
            issues.append(f"dialogue segment {sid} 缺少 speaker。")
        voice_line_id = item.get("voice_line_id")
        if voice_line_id and str(voice_line_id) not in voice_line_ids:
            issues.append(f"segment {sid} 引用了不存在的 voice_line_id：{voice_line_id}")
        if not voice_line_id:
            issues.append(f"segment {sid} 缺少 voice_line_id。")
    return segment_ids


def _validate_refs(items: list[dict[str, Any]], segment_ids: set[str], voice_line_ids: set[str], label: str, issues: list[str]) -> None:
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ref = item.get("segment_id")
        if ref and str(ref) not in segment_ids:
            issues.append(f"{label} 引用了不存在的 segment_id：{ref}")
        line_ref = item.get("voice_line_id")
        if line_ref and str(line_ref) not in voice_line_ids:
            issues.append(f"{label} 引用了不存在的 voice_line_id：{line_ref}")


def _validate_video_units(items: list[dict[str, Any]], voice_line_ids: set[str], issues: list[str]) -> None:
    if not isinstance(items, list) or not items:
        issues.append("script_video_unit_candidates 为空。")
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        unit_id = item.get("unit_candidate_id")
        refs = item.get("voice_line_ids") or []
        if not refs:
            issues.append(f"video unit {unit_id} 缺少 voice_line_ids。")
        for ref in refs:
            if str(ref) not in voice_line_ids:
                issues.append(f"video unit {unit_id} 引用了不存在的 voice_line_id：{ref}")
        duration = item.get("estimated_duration_sec")
        if isinstance(duration, (int, float)) and duration > 12:
            issues.append(f"video unit {unit_id} estimated_duration_sec 超过 12 秒：{duration}")
