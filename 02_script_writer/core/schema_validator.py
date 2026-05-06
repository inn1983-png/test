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
    "episode_split_plan",
    "script_version_strategy",
    "script_structure",
    "scene_beats",
    "script_emotion_curve",
    "voice_line_plan",
    "script_video_unit_candidates",
    "segments",
    "script_versions",
    "selected_version_id",
    "script_text",
    "source_line_usage",
    "tts_readability_report",
    "character_name_usage",
    "production_annotations",
    "audio_cues",
    "visual_dramatic_units",
    "visual_executability_report",
    "character_load_report",
    "continuity_chain",
    "storyboard_hints",
    "quality_report",
    "failure_learning_notes",
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

    visual_units = data.get("visual_dramatic_units", []) or []
    visual_unit_ids = _validate_visual_units(visual_units, segment_ids, voice_line_ids, issues)

    audio_cues = data.get("audio_cues", []) or []
    storyboard_hints = data.get("storyboard_hints", []) or []
    video_units = data.get("script_video_unit_candidates", []) or []

    _validate_refs(audio_cues, segment_ids, voice_line_ids, "audio_cues", issues)
    _validate_refs(storyboard_hints, segment_ids, voice_line_ids, "storyboard_hints", issues)
    _validate_video_units(video_units, voice_line_ids, issues)
    _validate_continuity_chain(data.get("continuity_chain", []) or [], visual_unit_ids, issues)
    _validate_script_versions(data.get("script_versions", []) or [], data.get("selected_version_id"), issues)

    event_coverage = data.get("event_coverage_map", []) or []
    if not event_coverage:
        issues.append("event_coverage_map 为空，无法确认 01 关键事件是否被剧本覆盖。")

    text = data.get("script_text", "")
    if not isinstance(text, str) or not text.strip():
        issues.append("script_text 为空。")

    _require_non_empty_list(data, "source_line_usage", "无法确认原文关键句是否被继承。", issues)
    _require_non_empty_list(data, "character_name_usage", "无法检查角色称呼一致性。", issues)
    _require_non_empty_list(data, "episode_split_plan", "无法判断长文案是否需要分集/分段。", issues)
    _require_non_empty_list(data, "script_emotion_curve", "无法检查剧本情绪曲线。", issues)
    _require_non_empty_list(data, "failure_learning_notes", "无法把真实测试失败样本回灌到后续精修。", issues)

    for key in ["tts_readability_report", "visual_executability_report", "character_load_report", "script_version_strategy"]:
        value = data.get(key)
        if not isinstance(value, dict) or not value:
            issues.append(f"{key} 为空或不是对象。")

    return {
        "passed": not issues,
        "issues": issues,
        "hard_rule_count": len(issues),
    }


def _require_non_empty_list(data: dict[str, Any], key: str, reason: str, issues: list[str]) -> None:
    value = data.get(key, []) or []
    if not isinstance(value, list) or not value:
        issues.append(f"{key} 为空，{reason}")


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


def _validate_visual_units(items: list[dict[str, Any]], segment_ids: set[str], voice_line_ids: set[str], issues: list[str]) -> set[str]:
    visual_unit_ids: set[str] = set()
    if not isinstance(items, list) or not items:
        issues.append("visual_dramatic_units 为空。")
        return visual_unit_ids
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            issues.append(f"visual_dramatic_units[{index}] 不是对象。")
            continue
        vid = item.get("visual_unit_id")
        if not vid:
            issues.append(f"visual_dramatic_units[{index}] 缺少 visual_unit_id。")
        elif str(vid) in visual_unit_ids:
            issues.append(f"visual_unit_id 重复：{vid}")
        else:
            visual_unit_ids.add(str(vid))
        ref = item.get("segment_id")
        if ref and str(ref) not in segment_ids:
            issues.append(f"visual_unit {vid} 引用了不存在的 segment_id：{ref}")
        line_ref = item.get("voice_line_id")
        if line_ref and str(line_ref) not in voice_line_ids:
            issues.append(f"visual_unit {vid} 引用了不存在的 voice_line_id：{line_ref}")
        if not item.get("action_chain"):
            issues.append(f"visual_unit {vid} 缺少 action_chain。")
    return visual_unit_ids


def _validate_continuity_chain(items: list[dict[str, Any]], visual_unit_ids: set[str], issues: list[str]) -> None:
    if not isinstance(items, list) or not items:
        issues.append("continuity_chain 为空。")
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ["from_visual_unit_id", "to_visual_unit_id"]:
            ref = item.get(key)
            if ref and str(ref) not in visual_unit_ids:
                issues.append(f"continuity_chain {key} 引用了不存在的 visual_unit_id：{ref}")
        if not item.get("must_keep"):
            issues.append("continuity_chain 存在条目缺少 must_keep。")


def _validate_script_versions(items: list[dict[str, Any]], selected_version_id: Any, issues: list[str]) -> None:
    if not isinstance(items, list) or not items:
        issues.append("script_versions 为空。")
        return
    version_ids = {str(item.get("version_id")) for item in items if isinstance(item, dict) and item.get("version_id")}
    if selected_version_id and str(selected_version_id) not in version_ids:
        issues.append(f"selected_version_id 不在 script_versions 中：{selected_version_id}")
    if not selected_version_id:
        issues.append("selected_version_id 为空。")
