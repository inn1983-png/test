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
    "script_structure",
    "segments",
    "script_text",
    "production_annotations",
    "audio_cues",
    "storyboard_hints",
    "quality_report",
]


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    missing = [key for key in TOP_LEVEL_REQUIRED if key not in data]
    if missing:
        issues.append(f"最终 script.json 缺少顶层字段：{', '.join(missing)}")

    segments = data.get("segments", []) or []
    if not isinstance(segments, list) or not segments:
        issues.append("segments 为空。")
        segment_ids: set[str] = set()
    else:
        segment_ids = _validate_segments(segments, issues)

    audio_cues = data.get("audio_cues", []) or []
    storyboard_hints = data.get("storyboard_hints", []) or []
    _validate_segment_refs(audio_cues, segment_ids, "audio_cues", issues)
    _validate_segment_refs(storyboard_hints, segment_ids, "storyboard_hints", issues)

    event_coverage = data.get("event_coverage_map", []) or []
    if not event_coverage:
        issues.append("event_coverage_map 为空，无法确认 01 关键事件是否被剧本覆盖。")

    text = data.get("script_text", "")
    if not isinstance(text, str) or not text.strip():
        issues.append("script_text 为空。")

    return {
        "passed": not issues,
        "issues": issues,
        "hard_rule_count": len(issues),
    }


def _validate_segments(segments: list[dict[str, Any]], issues: list[str]) -> set[str]:
    segment_ids: set[str] = set()
    allowed_types = {"os", "dialogue", "blank", "action", "emotion"}
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
        if stype not in allowed_types:
            issues.append(f"segment {sid} type 非法：{stype}")
        if stype in {"os", "dialogue", "action", "emotion"} and not item.get("text"):
            issues.append(f"segment {sid} 缺少 text。")
        if stype == "dialogue" and not item.get("speaker"):
            issues.append(f"dialogue segment {sid} 缺少 speaker。")
    return segment_ids


def _validate_segment_refs(items: list[dict[str, Any]], segment_ids: set[str], label: str, issues: list[str]) -> None:
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ref = item.get("segment_id")
        if ref and str(ref) not in segment_ids:
            issues.append(f"{label} 引用了不存在的 segment_id：{ref}")
