from __future__ import annotations

import re
from typing import Any


SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")


def split_paragraphs(novel_text: str, max_chars: int = 600) -> dict[str, Any]:
    """Create stable paragraph ids and raw text spans before LLM annotation.

    The LLM may classify and enrich paragraphs, but boundaries and paragraph_id
    should come from this deterministic splitter to keep evidence links stable.
    """
    text = novel_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = _split_raw_blocks(text)
    paragraphs = []
    cursor = 0
    index = 1

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        for piece in _split_long_block(block, max_chars=max_chars):
            start = text.find(piece, cursor)
            if start < 0:
                start = cursor
            end = start + len(piece)
            paragraph_id = f"p{index:03d}"
            paragraphs.append(
                {
                    "paragraph_id": paragraph_id,
                    "chapter_id": "chapter_001",
                    "index": index,
                    "text": piece,
                    "start_char": start,
                    "end_char": end,
                    "paragraph_type": "待LLM标注",
                    "contains_dialogue": _contains_dialogue(piece),
                    "contains_action": False,
                    "contains_new_character": False,
                    "contains_new_scene": False,
                    "contains_new_prop": False,
                }
            )
            cursor = end
            index += 1

    chapter = {
        "chapter_id": "chapter_001",
        "title": "第1章",
        "start_paragraph_id": paragraphs[0]["paragraph_id"] if paragraphs else None,
        "end_paragraph_id": paragraphs[-1]["paragraph_id"] if paragraphs else None,
        "paragraph_count": len(paragraphs),
        "core_conflict": "待LLM标注",
        "ending_hook": "待LLM标注",
    }
    return {"chapters": [chapter], "paragraphs": paragraphs, "timeline": []}


def paragraph_id_set(paragraphs: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("paragraph_id")) for item in paragraphs if item.get("paragraph_id")}


def merge_llm_paragraph_annotations(base: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, Any]:
    """Preserve deterministic paragraph boundaries and apply LLM annotations by id."""
    llm_by_id = {
        item.get("paragraph_id"): item
        for item in llm_output.get("paragraphs", [])
        if isinstance(item, dict) and item.get("paragraph_id")
    }
    merged_paragraphs = []
    for base_para in base.get("paragraphs", []):
        paragraph_id = base_para.get("paragraph_id")
        llm_para = llm_by_id.get(paragraph_id, {})
        merged = dict(base_para)
        for key in [
            "paragraph_type",
            "contains_dialogue",
            "contains_action",
            "contains_new_character",
            "contains_new_scene",
            "contains_new_prop",
        ]:
            if key in llm_para:
                merged[key] = llm_para[key]
        merged_paragraphs.append(merged)

    chapters = llm_output.get("chapters") if isinstance(llm_output.get("chapters"), list) else base.get("chapters", [])
    timeline = llm_output.get("timeline") if isinstance(llm_output.get("timeline"), list) else base.get("timeline", [])
    return {"chapters": chapters, "paragraphs": merged_paragraphs, "timeline": timeline}


def _split_raw_blocks(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
    if len(blocks) <= 1:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        blocks = lines if lines else ([text.strip()] if text.strip() else [])
    return blocks


def _split_long_block(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]
    sentences = [item for item in SENTENCE_SPLIT_RE.split(block) if item]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current += sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks or [block]


def _contains_dialogue(text: str) -> bool:
    return any(mark in text for mark in ["“", "”", "\"", "：", ":"])
