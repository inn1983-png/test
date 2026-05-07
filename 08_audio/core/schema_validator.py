from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("module") != "08_audio":
        issues.append("module must be 08_audio")
    if data.get("schema_version") not in {"1.0", "1.1"}:
        issues.append("schema_version must be 1.0 or 1.1")
    if data.get("stage_mode") != "audio_execution":
        issues.append("stage_mode must be audio_execution")
    if data.get("execution_mode") not in {"dry_run", "execute"}:
        issues.append("execution_mode must be dry_run or execute")

    final_audio_path = data.get("final_audio_path")
    if not isinstance(final_audio_path, str) or not final_audio_path:
        issues.append("final_audio_path is required")
    elif not Path(final_audio_path).exists():
        issues.append(f"final_audio_path does not exist: {final_audio_path}")

    for key in ("timeline_path", "subtitle_srt_path", "subtitle_ass_path"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            issues.append(f"{key} is required")
        elif not Path(value).exists():
            issues.append(f"{key} does not exist: {value}")

    if not isinstance(data.get("voice_queue"), list):
        issues.append("voice_queue must be a list")
    else:
        for idx, line in enumerate(data.get("voice_queue") or [], start=1):
            if not isinstance(line, dict):
                issues.append(f"voice_queue[{idx}] must be object")
                continue
            if str(line.get("line_type") or "").upper() not in {"S", "SILENCE", "留白"}:
                if not line.get("voice_id"):
                    issues.append(f"voice_queue[{idx}] missing voice_id")
                if not line.get("spk_audio_prompt"):
                    issues.append(f"voice_queue[{idx}] missing spk_audio_prompt")

    segments = data.get("segments")
    if not isinstance(segments, list):
        issues.append("segments must be a list")
    else:
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"segments[{idx}] must be object")
                continue
            for key in ("segment_id", "output_path", "status"):
                if not seg.get(key):
                    issues.append(f"segments[{idx}] missing {key}")
            if str(seg.get("line_type") or "").upper() not in {"S", "SILENCE", "留白"} and not seg.get("text"):
                issues.append(f"segments[{idx}] missing text")
            if seg.get("status") == "success" and not Path(str(seg.get("output_path"))).exists():
                issues.append(f"segments[{idx}] output_path does not exist")

    timeline = data.get("audio_timeline", {})
    if not isinstance(timeline, dict) or not isinstance(timeline.get("entries"), list):
        issues.append("audio_timeline.entries must be a list")

    if float(data.get("duration_seconds") or 0) <= 0:
        issues.append("duration_seconds must be > 0")

    return {"passed": not issues, "issues": issues}
