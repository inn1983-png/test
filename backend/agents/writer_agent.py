import re

from backend.app.node_store import save_node
from backend.app.canvas_store import refresh_canvas


PUNCT_SPLIT = re.compile(r"(?<=[。！？!?；;])")


def split_source(source_text, min_len=24, max_len=180):
    text = source_text.replace("\r\n", "\n").strip()
    raw_parts = []
    for paragraph in [p.strip() for p in text.split("\n") if p.strip()]:
        raw_parts.extend([p.strip() for p in PUNCT_SPLIT.split(paragraph) if p.strip()])
    segments = []
    buf = ""
    for part in raw_parts:
        if not buf:
            buf = part
        elif len(buf) + len(part) <= max_len:
            buf += part
        else:
            segments.append(buf)
            buf = part
    if buf:
        segments.append(buf)
    merged = []
    for seg in segments:
        if merged and len(seg) < min_len:
            merged[-1] += seg
        else:
            merged.append(seg)
    return merged or [source_text]


def classify_beat(text):
    conflict_words = ["骂", "打", "逼", "跪", "杀", "怒", "恨", "威胁", "羞辱", "不服", "反了"]
    turn_words = ["忽然", "没想到", "原来", "终于", "后来", "转身", "反手", "冷笑"]
    if any(w in text for w in turn_words):
        return "turn"
    if any(w in text for w in conflict_words):
        return "conflict"
    return "setup"


def make_script_block(index, text):
    beat = classify_beat(text)
    return {
        "id": "script_" + str(index).zfill(3),
        "type": "script_block",
        "status": "done",
        "source_ref": "source_001",
        "content": text,
        "beat": beat,
        "dialogue": [],
        "os": [text],
        "blank": "短暂停顿，保留情绪余味。",
        "screen_action": "按原文动作和情绪生成画面，不额外魔改核心设定。",
        "adaptation_rule": "不过度压缩；对白、OS、留白并行；保留高刺激原句。",
    }


def generate(project_id, source_text):
    segments = split_source(source_text)
    save_node(project_id, {
        "id": "source_001",
        "type": "source_text",
        "status": "done",
        "title": "source text",
        "content": source_text,
        "segment_count": len(segments),
    })
    for index, segment in enumerate(segments, start=1):
        save_node(project_id, {
            "id": "segment_" + str(index).zfill(3),
            "type": "story_segment",
            "status": "done",
            "source_ref": "source_001",
            "content": segment,
            "beat": classify_beat(segment),
        })
        save_node(project_id, make_script_block(index, segment))
    return refresh_canvas(project_id)
