from __future__ import annotations

from typing import Any


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100

    if stage_id == "09A":
        segments = data.get("segments") if isinstance(data.get("segments"), list) else []
        window_size = int(data.get("window_size") or 0)
        stride = int(data.get("stride") or 0)
        if not segments:
            issues.append("09A must build at least one video segment.")
        if window_size not in {4, 6, 9}:
            issues.append("09A window_size should be 4, 6, or 9.")
        if stride != max(1, window_size - 1):
            issues.append("09A stride must equal window_size - 1.")
        if not data.get("final_audio_path"):
            issues.append("09A missing final_audio_path.")
        previous_last = None
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"09A segment[{idx}] must be object.")
                continue
            for key in ("image_paths", "frame_ids", "audio_source_path", "output_clip_path", "start_seconds", "end_seconds", "ltx_prompt", "negative_prompt", "motion_policy"):
                if seg.get(key) in (None, "", []):
                    issues.append(f"09A {seg.get('segment_id', idx)} missing {key}.")
            frame_ids = seg.get("frame_ids") if isinstance(seg.get("frame_ids"), list) else []
            image_paths = seg.get("image_paths") if isinstance(seg.get("image_paths"), list) else []
            if len(frame_ids) != window_size:
                issues.append(f"09A {seg.get('segment_id', idx)} frame_ids length mismatch.")
            if len(image_paths) != window_size:
                issues.append(f"09A {seg.get('segment_id', idx)} image_paths length mismatch.")
            if previous_last and frame_ids and frame_ids[0] != previous_last:
                issues.append(f"09A {seg.get('segment_id', idx)} does not overlap previous segment tail frame.")
            if frame_ids:
                previous_last = frame_ids[-1]
            if float(seg.get("duration_seconds") or 0) > 12.5:
                issues.append(f"09A {seg.get('segment_id', idx)} duration exceeds 12.5 seconds.")
    elif stage_id == "09PRE":
        if data.get("status") == "blocked":
            failed_checks = data.get("failed_checks") if isinstance(data.get("failed_checks"), list) else []
            for check in failed_checks:
                if isinstance(check, dict):
                    issues.append(f"09PRE {check.get('check_id', 'unknown')}: {check.get('message', '')}")
        if data.get("preflight_mode") == "dry_run_lite":
            if data.get("status") != "success":
                issues.append("09PRE dry_run_lite must always succeed.")
    elif stage_id == "09B":
        results = data.get("execution_results") if isinstance(data.get("execution_results"), list) else []
        if not results:
            issues.append("09B must contain execution_results.")
        failed = [item for item in results if isinstance(item, dict) and item.get("status") != "success"]
        if failed:
            issues.append(f"09B has failed segments: {len(failed)}")
    elif stage_id == "09C":
        if not data.get("resume_manifest_path"):
            issues.append("09C missing resume_manifest_path.")
        if data.get("completed_count", 0) < 1:
            issues.append("09C no completed video clips.")
    elif stage_id == "09D":
        if data.get("merge_status") not in {"success", "skipped", "skipped_dry_run", "failed"}:
            issues.append("09D merge_status must be success, skipped, skipped_dry_run, or failed.")
        if data.get("final_video_ready"):
            if data.get("merge_status") != "success":
                issues.append("09D final_video_ready=true requires merge_status=success.")
            if not data.get("final_video_path"):
                issues.append("09D missing final_video_path.")
            probe = data.get("final_video_probe", {}) if isinstance(data.get("final_video_probe"), dict) else {}
            if probe and not probe.get("valid"):
                issues.append("09D final video ffprobe validation failed.")
        elif data.get("execution_mode") == "execute":
            issues.append(f"09D final_video not ready: {data.get('merge_error') or 'merge failed'}")
        elif not data.get("final_video_placeholder_path"):
            issues.append("09D dry_run should write final_video.placeholder.txt.")

    score -= min(80, len(issues) * 15)
    passed = score >= 70 and not issues
    return {
        "stage_id": stage_id,
        "score": score,
        "passed": passed,
        "issues": issues,
        "revision_instructions": [] if passed else ["09 是确定性执行阶段；优先重跑 failed_video_segments 或修复 ComfyUI/LTX2.3 workflow 映射，不回滚 06/07/08。"],
    }
