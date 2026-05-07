from __future__ import annotations

from pathlib import Path
from typing import Any


def _path_exists(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and Path(value).exists()


def _non_empty_path_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_valid_mp4(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    if not path.exists():
        return False
    if path.suffix.lower() != ".mp4":
        return False
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("module") != "10_final_assembly":
        issues.append("module must be 10_final_assembly")
    if data.get("schema_version") not in {"1.0", "1.1"}:
        issues.append("schema_version must be 1.0 or 1.1")
    if data.get("stage_mode") != "final_assembly":
        issues.append("stage_mode must be final_assembly")
    if data.get("uses_llm") is not False:
        issues.append("10_final_assembly must not use LLM")
    if data.get("uses_ltx") is not False:
        issues.append("10_final_assembly must not use LTX")
    if data.get("generates_new_video_segments") is not False:
        issues.append("10_final_assembly must not generate new video segments")

    for key in ("final_manifest_path", "final_meta_path"):
        if not _non_empty_path_string(data.get(key)):
            issues.append(f"{key} must be a non-empty target path")

    final_video_ready = data.get("final_video_ready")
    if final_video_ready is True:
        if not _is_valid_mp4(data.get("final_video_path")):
            issues.append(f"final_video_ready=true but final_video_path missing, does not exist, or is not a valid mp4: {data.get('final_video_path')}")
        if data.get("final_video_placeholder_path") is not None:
            issues.append("final_video_ready=true but final_video_placeholder_path should be null")
    elif final_video_ready is False:
        if data.get("final_video_path") is not None:
            issues.append("final_video_ready=false but final_video_path must be null")
        placeholder = data.get("final_video_placeholder_path")
        if placeholder and not _path_exists(placeholder):
            issues.append(f"final_video_ready=false and final_video_placeholder_path does not exist: {placeholder}")
    else:
        issues.append("final_video_ready must be true or false")

    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    if source.get("video_source_mode") not in {"final_video", "concat_clips", "dry_run_placeholder"}:
        issues.append("source.video_source_mode invalid")
    if source.get("audio_source") != "08_audio/final_audio.wav":
        issues.append("source.audio_source must be 08_audio/final_audio.wav")

    is_dry_run = source.get("video_source_mode") == "dry_run_placeholder"
    if not is_dry_run:
        for key in ("video_manifest_path", "final_audio_path"):
            if not _path_exists(data.get(key)):
                issues.append(f"{key} missing or does not exist: {data.get(key)}")

    subtitle_policy = data.get("subtitle_policy") if isinstance(data.get("subtitle_policy"), dict) else {}
    if subtitle_policy.get("default_burn_subtitles") is not False:
        issues.append("default_burn_subtitles must be false")
    if subtitle_policy.get("burn_subtitles") not in {True, False}:
        issues.append("burn_subtitles must be boolean")

    stage_status = data.get("stage_status")
    if not isinstance(stage_status, list) or len(stage_status) != 4:
        issues.append("stage_status must contain 10A/10B/10C/10D")
    else:
        expected = ["10A", "10B", "10C", "10D"]
        got = [item.get("stage_id") for item in stage_status if isinstance(item, dict)]
        if got != expected:
            issues.append(f"stage_status order must be {expected}, got {got}")

    return {"passed": not issues, "issues": issues}
