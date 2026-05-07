from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("module") != "09_video":
        issues.append("module must be 09_video")
    if data.get("schema_version") not in {"1.0", "1.1"}:
        issues.append("schema_version must be 1.0 or 1.1")
    if data.get("stage_mode") != "video_execution":
        issues.append("stage_mode must be video_execution")
    if data.get("execution_mode") not in {"dry_run", "execute"}:
        issues.append("execution_mode must be dry_run or execute")

    window_size = int(data.get("window_size") or 0)
    stride = int(data.get("stride") or 0)
    if window_size not in {4, 6, 9}:
        issues.append("window_size should be 4, 6, or 9 for the verified keyframe-window workflows")
    if stride != max(1, window_size - 1):
        issues.append("stride must equal window_size - 1")

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
        previous_last_frame = None
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"video_segments[{idx}] must be object")
                continue
            if int(seg.get("segment_index") or -1) != expected_index:
                issues.append(f"video_segments[{idx}] segment_index must be {expected_index}")
            expected_index += 1
            for key in ("segment_id", "audio_source_path", "output_clip_path", "status", "ltx_prompt", "negative_prompt", "motion_policy"):
                if not seg.get(key):
                    issues.append(f"video_segments[{idx}] missing {key}")
            frame_ids = seg.get("frame_ids")
            image_paths = seg.get("image_paths")
            seg_window_size = int(seg.get("window_size") or window_size or 0)
            if not isinstance(frame_ids, list) or len(frame_ids) != seg_window_size:
                issues.append(f"video_segments[{idx}] frame_ids length must equal window_size")
            if not isinstance(image_paths, list) or len(image_paths) != seg_window_size:
                issues.append(f"video_segments[{idx}] image_paths length must equal window_size")
            else:
                for image_idx, image_path in enumerate(image_paths, start=1):
                    if not isinstance(image_path, str) or not image_path:
                        issues.append(f"video_segments[{idx}] image_paths[{image_idx}] is empty")
            if idx > 1 and isinstance(frame_ids, list) and previous_last_frame and frame_ids:
                if frame_ids[0] != previous_last_frame:
                    issues.append(f"video_segments[{idx}] first frame must equal previous segment last frame for overlap continuity")
            if isinstance(frame_ids, list) and frame_ids:
                previous_last_frame = frame_ids[-1]
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
