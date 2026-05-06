from __future__ import annotations

from typing import Any


def chunk_paragraphs(paragraphs: list[dict[str, Any]], max_chars: int = 6000, overlap: int = 1) -> list[dict[str, Any]]:
    """Split paragraphs into stable batches for LLM extraction.

    overlap keeps a small amount of context between adjacent batches. Duplicate
    candidates are expected and will be merged downstream.
    """
    if not paragraphs:
        return []

    batches: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    batch_index = 1

    for para in paragraphs:
        text = str(para.get("text", ""))
        if current and current_chars + len(text) > max_chars:
            batches.append(_make_batch(batch_index, current))
            batch_index += 1
            current = current[-overlap:] if overlap > 0 else []
            current_chars = sum(len(str(item.get("text", ""))) for item in current)
        current.append(para)
        current_chars += len(text)

    if current:
        batches.append(_make_batch(batch_index, current))

    return batches


def _make_batch(index: int, paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "batch_id": f"batch_{index:03d}",
        "paragraph_ids": [item.get("paragraph_id") for item in paragraphs],
        "start_paragraph_id": paragraphs[0].get("paragraph_id") if paragraphs else None,
        "end_paragraph_id": paragraphs[-1].get("paragraph_id") if paragraphs else None,
        "paragraphs": paragraphs,
    }


def merge_candidate_batches(batch_outputs: list[dict[str, Any]], base_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge batch candidate outputs without deleting uncertain duplicates."""
    characters: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    props: list[dict[str, Any]] = []
    asset_binding_hints: list[dict[str, Any]] = []
    visual_risk_report: dict[str, list[Any]] = {}

    for output in batch_outputs:
        batch_id = output.get("batch_id")
        for key, target in [
            ("candidate_characters", characters),
            ("candidate_scenes", scenes),
            ("candidate_props", props),
        ]:
            for item in output.get(key, []) or []:
                if isinstance(item, dict):
                    copied = dict(item)
                    copied.setdefault("source_batch_id", batch_id)
                    target.append(copied)
        asset_binding_hints.extend(output.get("asset_binding_hints", []) or [])
        risks = output.get("visual_risk_report", {}) or {}
        if isinstance(risks, dict):
            for key, value in risks.items():
                if isinstance(value, list):
                    visual_risk_report.setdefault(key, []).extend(value)
                elif value:
                    visual_risk_report.setdefault(key, []).append(value)

    return {
        "candidate_extraction_policy": base_policy or {"mode": "extract_every_mentioned_candidate"},
        "candidate_characters": _assign_ids(characters, "char_candidate"),
        "candidate_scenes": _assign_ids(scenes, "scene_candidate"),
        "candidate_props": _assign_ids(props, "prop_candidate"),
        "asset_binding_hints": asset_binding_hints,
        "visual_risk_report": visual_risk_report,
        "batch_count": len(batch_outputs),
    }


def _assign_ids(items: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(items, start=1):
        copied = dict(item)
        copied["candidate_id"] = copied.get("candidate_id") or f"{prefix}_{index:03d}"
        result.append(copied)
    return result
