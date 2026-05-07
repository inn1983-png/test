from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("module") != "08_audio":
        issues.append("module must be 08_audio")
    if data.get("schema_version") != "1.0":
        issues.append("schema_version must be 1.0")
    if data.get("stage_mode") != "audio_execution":
        issues.append("stage_mode must be audio_execution")
    if data.get("execution_mode") not in {"dry_run", "execute"}:
        issues.append("execution_mode must be dry_run or execute")

    final_audio_path = data.get("final_audio_path")
    if not isinstance(final_audio_path, str) or not final_audio_path:
        issues.append("final_audio_path is required")
    elif not Path(final_audio_path).exists():
        issues.append(f"final_audio_path does not exist: {final_audio_path}")

    segments = data.get("segments")
    if not isinstance(segments, list):
        issues.append("segments must be a list")
    else:
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"segments[{idx}] must be object")
                continue
            for key in ("segment_id", "text", "output_path", "status"):
                if not seg.get(key):
                    issues.append(f"segments[{idx}] missing {key}")
            if seg.get("status") == "success" and not Path(str(seg.get("output_path"))).exists():
                issues.append(f"segments[{idx}] output_path does not exist")

    if float(data.get("duration_seconds") or 0) <= 0:
        issues.append("duration_seconds must be > 0")

    return {"passed": not issues, "issues": issues}
