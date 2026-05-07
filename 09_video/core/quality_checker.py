from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100

    if stage_id == "09A":
        segments = data.get("segments") if isinstance(data.get("segments"), list) else []
        if not segments:
            issues.append("09A must build at least one video segment.")
        if not data.get("final_audio_path"):
            issues.append("09A missing final_audio_path.")
        for idx, seg in enumerate(segments, start=1):
            if not isinstance(seg, dict):
                issues.append(f"09A segment[{idx}] must be object.")
                continue
            for key in ("image_path", "audio_source_path", "output_clip_path", "start_seconds", "end_seconds"):
                if seg.get(key) in (None, ""):
                    issues.append(f"09A {seg.get('segment_id', idx)} missing {key}.")
            if float(seg.get("duration_seconds") or 0) > 12.5:
                issues.append(f"09A {seg.get('segment_id', idx)} duration exceeds 12.5 seconds.")
    elif stage_id == "09B":
        results = data.get("execution_results") if isinstance(data.get("execution_results"), list) else []
        if not results:
            issues.append("09B must contain execution_results.")
        failed = [item for item in results if isinstance(item, dict) and item.get("status") not in {"success", "submitted"}]
        if failed:
            issues.append(f"09B has failed segments: {len(failed)}")
    elif stage_id == "09C":
        if not data.get("resume_manifest_path"):
            issues.append("09C missing resume_manifest_path.")
        if data.get("completed_count", 0) < 1:
            issues.append("09C no completed video clips.")
    elif stage_id == "09D":
        if data.get("merge_status") not in {"success", "planned"}:
            issues.append("09D merge_status must be success or planned.")
        if not data.get("final_video_path"):
            issues.append("09D missing final_video_path.")

    score -= min(80, len(issues) * 15)
    passed = score >= 70 and not issues
    return {
        "stage_id": stage_id,
        "score": score,
        "passed": passed,
        "issues": issues,
        "revision_instructions": [] if passed else ["09 是确定性执行阶段；优先重跑 failed_video_segments 或修复 ComfyUI/LTX2.3 workflow 映射，不回滚 06/07/08。"],
    }
