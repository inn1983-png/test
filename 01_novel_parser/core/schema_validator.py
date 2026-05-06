from __future__ import annotations

from typing import Any


TOP_LEVEL_REQUIRED = [
    "story_understanding",
    "story_spine",
    "chapters",
    "paragraphs",
    "event_graph",
    "candidate_characters",
    "candidate_scenes",
    "candidate_props",
    "voice_line_candidates",
    "video_unit_candidates",
    "evidence_index",
    "quality_report",
]


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    missing = [key for key in TOP_LEVEL_REQUIRED if key not in data]
    if missing:
        issues.append(f"最终 novel_analysis.json 缺少顶层字段：{', '.join(missing)}")

    paragraphs = data.get("paragraphs", []) or []
    paragraph_ids = _id_set(paragraphs, "paragraph_id")
    event_graph = data.get("event_graph", {}) or {}
    events = event_graph.get("events", []) if isinstance(event_graph, dict) else []
    event_ids = _id_set(events, "event_id")

    if not paragraphs:
        issues.append("paragraphs 为空。")
    if not events:
        issues.append("event_graph.events 为空。")

    _validate_event_refs(events, paragraph_ids, issues)
    _validate_event_edges(event_graph.get("event_edges", []) if isinstance(event_graph, dict) else [], event_ids, issues)
    _validate_candidate_refs(data.get("candidate_characters", []), paragraph_ids, "candidate_characters", issues)
    _validate_candidate_refs(data.get("candidate_scenes", []), paragraph_ids, "candidate_scenes", issues)
    _validate_candidate_refs(data.get("candidate_props", []), paragraph_ids, "candidate_props", issues)
    _validate_voice_refs(data.get("voice_line_candidates", []), paragraph_ids, event_ids, issues)
    _validate_video_refs(data.get("video_unit_candidates", []), event_ids, issues)
    _validate_evidence_refs(data.get("evidence_index", []), paragraph_ids, issues)

    return {
        "passed": not issues,
        "issues": issues,
        "hard_rule_count": len(issues),
    }


def _id_set(items: list[dict[str, Any]], key: str) -> set[str]:
    return {str(item.get(key)) for item in items if isinstance(item, dict) and item.get(key)}


def _validate_event_refs(events: list[dict[str, Any]], paragraph_ids: set[str], issues: list[str]) -> None:
    for event in events or []:
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id")
        refs = event.get("paragraph_ids", []) or []
        if not refs:
            issues.append(f"事件 {event_id} 缺少 paragraph_ids。")
        for ref in refs:
            if str(ref) not in paragraph_ids:
                issues.append(f"事件 {event_id} 引用了不存在的 paragraph_id：{ref}")


def _validate_event_edges(edges: list[dict[str, Any]], event_ids: set[str], issues: list[str]) -> None:
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        for key in ["from_event", "to_event"]:
            value = edge.get(key)
            if value and str(value) not in event_ids:
                issues.append(f"event_edges 引用了不存在的 event_id：{value}")


def _validate_candidate_refs(candidates: list[dict[str, Any]], paragraph_ids: set[str], label: str, issues: list[str]) -> None:
    for item in candidates or []:
        if not isinstance(item, dict):
            continue
        cid = item.get("candidate_id") or item.get("name")
        refs = set(item.get("appearance_paragraphs", []) or [])
        first = item.get("first_appearance_paragraph")
        if first:
            refs.add(first)
        for mention in item.get("raw_mentions", []) or []:
            if isinstance(mention, dict) and mention.get("paragraph_id"):
                refs.add(mention.get("paragraph_id"))
        if not refs:
            issues.append(f"{label} 候选 {cid} 缺少 paragraph 引用。")
        for ref in refs:
            if str(ref) not in paragraph_ids:
                issues.append(f"{label} 候选 {cid} 引用了不存在的 paragraph_id：{ref}")


def _validate_voice_refs(items: list[dict[str, Any]], paragraph_ids: set[str], event_ids: set[str], issues: list[str]) -> None:
    for item in items or []:
        if not isinstance(item, dict):
            continue
        vid = item.get("line_candidate_id")
        for ref in item.get("source_paragraph_ids", []) or []:
            if str(ref) not in paragraph_ids:
                issues.append(f"voice_line {vid} 引用了不存在的 paragraph_id：{ref}")
        event_id = item.get("source_event_id")
        if event_id and str(event_id) not in event_ids:
            issues.append(f"voice_line {vid} 引用了不存在的 event_id：{event_id}")


def _validate_video_refs(items: list[dict[str, Any]], event_ids: set[str], issues: list[str]) -> None:
    for item in items or []:
        if not isinstance(item, dict):
            continue
        uid = item.get("unit_candidate_id")
        event_id = item.get("event_id")
        if event_id and str(event_id) not in event_ids:
            issues.append(f"video_unit {uid} 引用了不存在的 event_id：{event_id}")


def _validate_evidence_refs(items: list[dict[str, Any]], paragraph_ids: set[str], issues: list[str]) -> None:
    for item in items or []:
        if not isinstance(item, dict):
            continue
        eid = item.get("evidence_id")
        ref = item.get("paragraph_id")
        if ref and str(ref) not in paragraph_ids:
            issues.append(f"evidence {eid} 引用了不存在的 paragraph_id：{ref}")
