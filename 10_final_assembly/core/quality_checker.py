from __future__ import annotations

from pathlib import Path
from typing import Any


def _exists(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and Path(value).exists()


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100

    if stage_id == "10A":
        if not data.get("video_manifest_path"):
            issues.append("10A missing 09_video/video_manifest.json.")
        if not data.get("final_audio_path"):
            issues.append("10A missing 08_audio/final_audio.wav.")
        if not data.get("preferred_video_path") and not data.get("clip_paths"):
            issues.append("10A needs 09_video/final_video.mp4 or valid clips from video_segments.")
    elif stage_id == "10B":
        if data.get("video_source_mode") not in {"final_video", "concat_clips", "dry_run_placeholder"}:
            issues.append("10B video_source_mode invalid.")
        if not data.get("prepared_video_path"):
            issues.append("10B missing prepared_video_path.")
    elif stage_id == "10C":
        if not data.get("final_audio_path"):
            issues.append("10C missing final_audio_path.")
        copied = data.get("copied_subtitles") if isinstance(data.get("copied_subtitles"), list) else []
        missing = data.get("missing_subtitles") if isinstance(data.get("missing_subtitles"), list) else []
        if not copied and len(missing) >= 2:
            issues.append("10C found no subtitle.srt or subtitle.ass; allowed, but needs review if subtitles were expected.")
    elif stage_id == "10D":
        if not data.get("final_video_path"):
            issues.append("10D missing final_video_path.")
        if data.get("export_mode") not in {"mux", "burn_subtitles", "skip_existing", "dry_run_placeholder"}:
            issues.append("10D export_mode invalid.")
        if data.get("status") not in {"success", "skipped", "needs_review"}:
            issues.append("10D status invalid.")

    score -= min(80, len(issues) * 15)
    passed = score >= 70 and not issues
    return {
        "stage_id": stage_id,
        "score": score,
        "passed": passed,
        "issues": issues,
        "revision_instructions": [] if passed else ["10 是确定性最终包装层；请修复 08/09 产物路径、安装 ffmpeg，或开启 dry_run 检查 manifest。"],
    }
