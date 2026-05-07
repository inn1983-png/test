from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text_of(item: dict[str, Any]) -> str:
    for key in ("text", "line", "content", "dialogue", "os", "voice_text", "narration"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _speaker_of(item: dict[str, Any]) -> str:
    for key in ("speaker", "character", "role", "name", "voice_role"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    kind = str(item.get("type") or item.get("line_type") or "").lower()
    if kind in {"os", "narration", "旁白", "内心"}:
        return "OS"
    return "Narrator"


def _emotion_of(item: dict[str, Any]) -> str:
    for key in ("emotion", "tone", "mood", "delivery", "voice_emotion"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "calm"


def _collect_candidates(script: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for key in ("voice_lines", "audio_lines", "dialogue_lines", "narration_lines"):
        for item in _as_list(script.get(key)):
            if isinstance(item, dict):
                candidates.append(item)

    for segment in _as_list(script.get("segments")):
        if not isinstance(segment, dict):
            continue
        for key in ("voice_lines", "lines", "dialogues", "dialogue", "narrations"):
            for item in _as_list(segment.get(key)):
                if isinstance(item, dict):
                    merged = {"segment_id": segment.get("segment_id") or segment.get("id"), **item}
                    candidates.append(merged)

    for unit in _as_list(script.get("visual_dramatic_units")):
        if not isinstance(unit, dict):
            continue
        for key in ("voice_lines", "dialogue_lines", "lines"):
            for item in _as_list(unit.get(key)):
                if isinstance(item, dict):
                    merged = {"visual_unit_id": unit.get("visual_unit_id") or unit.get("id"), **item}
                    candidates.append(merged)

    return candidates


def build_voice_queue(script: dict[str, Any]) -> dict[str, Any]:
    """Extract a stable audio queue from the flexible 02_script_writer output."""
    lines: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, item in enumerate(_collect_candidates(script), start=1):
        text = _text_of(item)
        if not text:
            continue
        speaker = _speaker_of(item)
        line_id = str(item.get("voice_line_id") or item.get("line_id") or item.get("id") or f"audio_line_{index:04d}")
        dedupe_key = (line_id, speaker, text)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        kind = str(item.get("type") or item.get("line_type") or "dialogue")
        lines.append(
            {
                "audio_line_id": line_id,
                "source_segment_id": item.get("segment_id"),
                "source_visual_unit_id": item.get("visual_unit_id"),
                "speaker": speaker,
                "line_type": kind,
                "text": text,
                "emotion": _emotion_of(item),
                "speed_hint": item.get("speed_hint") or item.get("pace") or "normal",
                "pause_after_seconds": float(item.get("pause_after_seconds") or 0.15),
                "source": "02_script_writer",
            }
        )

    if not lines:
        fallback_text = script.get("script_text") or script.get("final_script") or script.get("content") or ""
        if isinstance(fallback_text, str) and fallback_text.strip():
            lines.append(
                {
                    "audio_line_id": "audio_line_0001",
                    "source_segment_id": None,
                    "source_visual_unit_id": None,
                    "speaker": "Narrator",
                    "line_type": "fallback_text",
                    "text": fallback_text.strip(),
                    "emotion": "calm",
                    "speed_hint": "normal",
                    "pause_after_seconds": 0.15,
                    "source": "02_script_writer.fallback_text",
                }
            )

    return {
        "stage": "08A_audio_queue_build",
        "status": "success" if lines else "needs_review",
        "voice_queue": lines,
        "speaker_count": len({line["speaker"] for line in lines}),
        "line_count": len(lines),
        "notes": [
            "08A 只从 02 剧本提取对白/OS/旁白音频队列，不重新改写剧情。",
            "如果 02 已有 voice_lines/audio_lines，会优先使用；否则尝试从 segments / visual_dramatic_units 中提取。",
        ],
    }
