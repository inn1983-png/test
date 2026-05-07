from __future__ import annotations

from pathlib import Path
from typing import Any


def build_timeline(segments: list[dict[str, Any]], final_audio_path: str, output_dir: str | Path) -> dict[str, Any]:
    cursor = 0.0
    entries: list[dict[str, Any]] = []
    for seg in segments:
        if not isinstance(seg, dict) or seg.get("status") != "success":
            continue
        duration = float(seg.get("actual_duration_seconds") or seg.get("estimated_duration_seconds") or 0)
        pause = float(seg.get("pause_after_seconds") or 0)
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        entries.append(
            {
                "audio_line_id": seg.get("audio_line_id"),
                "segment_id": seg.get("segment_id"),
                "speaker": seg.get("speaker"),
                "line_type": seg.get("line_type"),
                "text": seg.get("text"),
                "emotion": seg.get("emotion"),
                "voice_id": seg.get("voice_id"),
                "start_time": start,
                "end_time": end,
                "duration_seconds": round(duration, 3),
                "pause_after_seconds": round(pause, 3),
                "audio_path": seg.get("output_path"),
                "lip_sync_required": str(seg.get("line_type") or "").upper() in {"D", "DIALOGUE", "对白"},
            }
        )
        cursor = end + pause

    timeline = {
        "schema_version": "1.0",
        "final_audio_path": final_audio_path,
        "duration_seconds": round(cursor, 3),
        "entries": entries,
        "video_unit_policy": {
            "min_segment_seconds": 6,
            "max_segment_seconds": 12,
            "split_hint": "如果单条 voice_line 加起势和末帧留白后超过 12 秒，优先回到 02 拆句，不在 09 硬救。",
        },
    }
    return timeline


def _srt_time(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(timeline: dict[str, Any]) -> str:
    blocks: list[str] = []
    for idx, entry in enumerate(timeline.get("entries", []) or [], start=1):
        if not isinstance(entry, dict):
            continue
        speaker = entry.get("speaker") or ""
        text = entry.get("text") or ""
        caption = f"{speaker}：{text}" if speaker and speaker not in {"Narrator", "OS"} else str(text)
        blocks.append(
            "\n".join(
                [
                    str(idx),
                    f"{_srt_time(float(entry.get('start_time') or 0))} --> {_srt_time(float(entry.get('end_time') or 0))}",
                    caption,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def build_ass(timeline: dict[str, Any]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,54,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = []
    for entry in timeline.get("entries", []) or []:
        if not isinstance(entry, dict):
            continue
        start = _srt_time(float(entry.get("start_time") or 0)).replace(",", ".")[:-1]
        end = _srt_time(float(entry.get("end_time") or 0)).replace(",", ".")[:-1]
        speaker = entry.get("speaker") or ""
        text = str(entry.get("text") or "").replace("\n", "\\N")
        caption = f"{speaker}：{text}" if speaker and speaker not in {"Narrator", "OS"} else text
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{caption}")
    return header + "\n".join(lines) + ("\n" if lines else "")
