from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("module") != "09_video":
        issues.append("module must be 09_video")
    if data.get("schema_version") not in {"1.0"}:
        issues.append("schema_version must be 1.0")
    if data.get("stage_mode") != "video_execution":
        issues.append("stage_mode must be video_execution")
    if data.get("execution_mode") not in {"dry_run", "execute"}:
        issues.append("execution_mode must be dry_run or execute")

    for key in ("final_audio_path", "video_plan_path", "resume_manifest_path"):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            issues.append(f"{key} is required")
        elif not Path(value).exists():
            issues.append(f"{key} does not exist: {value}")

    segments = data.get("video_segments")
    if not isinstance(segments, list) or not segments:
        issues.append("video_segments must be a non-empty list")
    else:
        expected_index = 1
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"video_segments[{idx}] must be object")
                continue
            if int(seg.get("segment_index") or -1) != expected_index:
                issues.append(f"video_segments[{idx}] segment_index must be {expected_index}")
            expected_index += 1
            for key in ("segment_id", "image_path", "audio_source_path", "output_clip_path", "status"):
                if not seg.get(key):
                    issues.append(f"video_segments[{idx}] missing {key}")
            if seg.get("status") == "success" and not Path(str(seg.get("output_clip_path"))).exists():
                issues.append(f"video_segments[{idx}] output_clip_path does not exist")
            if float(seg.get("duration_seconds") or 0) <= 0:
                issues.append(f"video_segments[{idx}] duration_seconds must be > 0")
            if float(seg.get("duration_seconds") or 0) > 12.5:
                issues.append(f"video_segments[{idx}] duration_seconds exceeds 12.5 seconds")

    final_video_path = data.get("final_video_path")
    if final_video_path:
        if data.get("merge_status") == "success" and not Path(str(final_video_path)).exists():
            issues.append(f"final_video_path does not exist: {final_video_path}")
    else:
        issues.append("final_video_path is required")

    retry_plan = data.get("retry_plan")
    if not isinstance(retry_plan, dict):
        issues.append("retry_plan must be object")
    return {"passed": not issues, "issues": issues}
