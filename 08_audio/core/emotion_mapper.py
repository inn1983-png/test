from __future__ import annotations

from typing import Any

EMOTION_MAP: dict[str, dict[str, Any]] = {
    "愤怒": {"emo_text": "愤怒，压低声音，带有克制的火气", "emo_vector": [0, 0.85, 0, 0, 0.2, 0, 0, 0.1], "emo_alpha": 0.75},
    "压抑": {"emo_text": "压抑，低沉，克制，带一点悲凉", "emo_vector": [0, 0.15, 0.25, 0, 0, 0.65, 0, 0.35], "emo_alpha": 0.6},
    "悲伤": {"emo_text": "悲伤，低落，声音发紧", "emo_vector": [0, 0, 0.8, 0, 0, 0.25, 0, 0.1], "emo_alpha": 0.65},
    "恐惧": {"emo_text": "恐惧，紧张，急促，带颤抖", "emo_vector": [0, 0, 0.1, 0.85, 0, 0, 0.2, 0], "emo_alpha": 0.7},
    "震惊": {"emo_text": "震惊，短促，难以置信", "emo_vector": [0, 0, 0, 0.1, 0, 0, 0.85, 0.1], "emo_alpha": 0.65},
    "冷静": {"emo_text": "冷静，平稳，清晰", "emo_vector": [0, 0, 0, 0, 0, 0, 0, 0.85], "emo_alpha": 0.45},
    "冷笑": {"emo_text": "冷笑，讥讽，平静中带轻蔑", "emo_vector": [0.1, 0.25, 0, 0, 0.45, 0, 0, 0.45], "emo_alpha": 0.55},
    "紧张": {"emo_text": "紧张，语速略快，呼吸收紧", "emo_vector": [0, 0.15, 0, 0.55, 0, 0, 0.25, 0.15], "emo_alpha": 0.6},
    "平静": {"emo_text": "平静，自然，清晰", "emo_vector": [0, 0, 0, 0, 0, 0, 0, 0.8], "emo_alpha": 0.45},
    "calm": {"emo_text": "calm, natural, clear", "emo_vector": [0, 0, 0, 0, 0, 0, 0, 0.8], "emo_alpha": 0.45},
}


def map_emotion(raw: str | None, line_type: str | None = None) -> dict[str, Any]:
    text = (raw or "calm").strip() or "calm"
    lowered = text.lower()
    for key, value in EMOTION_MAP.items():
        if key in text or key.lower() in lowered:
            mapped = {"raw_emotion": text, "emotion_key": key, **value}
            break
    else:
        mapped = {
            "raw_emotion": text,
            "emotion_key": "custom",
            "emo_text": text,
            "emo_vector": None,
            "emo_alpha": 0.6,
        }

    kind = (line_type or "").upper()
    if kind in {"N", "NARRATION", "旁白"}:
        mapped["emo_alpha"] = min(float(mapped.get("emo_alpha") or 0.6), 0.45)
        mapped["emotion_policy"] = "narrator_weak_emotion"
    elif kind in {"M", "OS", "心理", "内心"}:
        mapped["emo_alpha"] = min(float(mapped.get("emo_alpha") or 0.6), 0.6)
        mapped["emotion_policy"] = "monologue_medium_emotion"
    elif kind in {"S", "SILENCE", "留白"}:
        mapped["emo_alpha"] = 0.0
        mapped["emotion_policy"] = "silence_no_emotion"
    else:
        mapped["emotion_policy"] = "dialogue_full_emotion"
    return mapped


def apply_emotion_mapping(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in queue:
        if not isinstance(line, dict):
            continue
        mapped = map_emotion(str(line.get("emotion") or "calm"), str(line.get("line_type") or ""))
        result.append({**line, "emotion_mapping": mapped})
    return result
