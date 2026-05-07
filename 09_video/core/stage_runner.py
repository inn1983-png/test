from __future__ import annotations

import os
import shutil
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any

io_utils = import_module("00_common.io_utils")
workflow_adapter = import_module("09_video.core.workflow_adapter")
comfyui_client = import_module("09_video.core.comfyui_client")
quality_checker = import_module("09_video.core.quality_checker")
schema_validator = import_module("09_video.core.schema_validator")

SCHEMA_VERSION = "1.1"

STAGES: list[dict[str, str]] = [
    {"stage_id": "09A", "name": "window_segment_plan", "output_file": "09A_video_segment_plan.json"},
    {"stage_id": "09B", "name": "ltx23_comfyui_one_window_execution", "output_file": "09B_ltx23_execution.json"},
    {"stage_id": "09C", "name": "breakpoint_resume_scan", "output_file": "09C_resume_scan.json"},
    {"stage_id": "09D", "name": "final_merge_and_manifest_check", "output_file": "09D_final_merge.json"},
]


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _run_and_score(stage_id: str, data: dict[str, Any], output_dir: str | Path, output_file: str) -> dict[str, Any]:
    quality = quality_checker.evaluate_stage(stage_id, data)
    data["stage_quality"] = quality
    output_path = _write_stage(output_dir, output_file, data)
    return {"stage_id": stage_id, "status": "success" if quality["passed"] else "needs_review", "output_path": output_path, "quality": quality}


def run_09b(plan: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    client = comfyui_client.ComfyUIClient()
    results: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for segment in plan.get("segments", []) or []:
        if not isinstance(segment, dict):
            continue
        try:
            result = client.submit_segment(segment, output_dir)
        except Exception as exc:
            result = {
                "status": "failed",
                "execution_mode": "execute" if not client.dry_run else "dry_run",
                "segment_id": segment.get("segment_id"),
                "output_clip_path": segment.get("output_clip_path"),
                "error": str(exc),
            }
        results.append(result)
        if result.get("status") not in {"success", "submitted"}:
            failed.append(result)
    return {
        "stage": "09B_ltx23_comfyui_one_window_execution",
        "status": "needs_retry" if failed else "success",
        "execution_mode": "dry_run" if client.dry_run else "execute",
        "execution_results": results,
        "failed_video_segments": failed,
        "notes": [
            "09B 采用外部 Python 一段一提交；ComfyUI 每次只跑一组关键帧窗口。",
            "已有 clip 文件默认跳过，形成断点续跑；需要重抽卡时设置 AI_DRAMA_VIDEO_FORCE_RERUN=1。",
        ],
    }


def run_09c(plan: dict[str, Any], execution: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    results_by_id = {r.get("segment_id"): r for r in execution.get("execution_results", []) or [] if isinstance(r, dict)}
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for segment in plan.get("segments", []) or []:
        if not isinstance(segment, dict):
            continue
        result = results_by_id.get(segment.get("segment_id"), {})
        clip_path = Path(str(result.get("output_clip_path") or segment.get("output_clip_path")))
        exists = clip_path.exists()
        status = "success" if exists else "missing"
        row = {**segment, "status": status, "resume_hit": bool(result.get("resume_hit")), "prompt_id": result.get("prompt_id"), "output_clip_path": str(clip_path), "execution_result": result}
        rows.append(row)
        if not exists:
            missing.append({"segment_id": segment.get("segment_id"), "output_clip_path": str(clip_path), "reason": "clip file missing"})
    resume_manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": "09C_breakpoint_resume_scan",
        "status": "needs_retry" if missing else "success",
        "completed_count": len(rows) - len(missing),
        "missing_count": len(missing),
        "segments": rows,
        "missing_segments": missing,
        "resume_policy": {"skip_existing_clips": True, "force_rerun_env": "AI_DRAMA_VIDEO_FORCE_RERUN=1", "retry_scope": "failed_video_segments_only" if missing else "none"},
    }
    path = Path(output_dir) / "resume_manifest.json"
    io_utils.write_json(path, resume_manifest)
    return {**resume_manifest, "resume_manifest_path": str(path)}


def _merge_with_ffmpeg(segments: list[dict[str, Any]], final_path: Path) -> bool:
    ffmpeg = os.getenv("AI_DRAMA_FFMPEG", "ffmpeg")
    if not shutil.which(ffmpeg):
        return False
    list_path = final_path.parent / "concat_list.txt"
    lines: list[str] = []
    for seg in segments:
        path = Path(str(seg.get("output_clip_path") or ""))
        if not path.exists():
            return False
        lines.append(f"file '{path.as_posix()}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(final_path)]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return result.returncode == 0 and final_path.exists()


def run_09d(plan: dict[str, Any], resume: dict[str, Any], final_audio_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    final_path = output_dir / "final_video.mp4"
    segments = [seg for seg in resume.get("segments", []) or [] if isinstance(seg, dict) and seg.get("status") == "success"]
    merge_enabled = os.getenv("AI_DRAMA_VIDEO_AUTO_MERGE", "1").strip().lower() not in {"0", "false", "no", "off"}
    merge_status = "planned"
    merge_note = "Merge skipped or planned."
    if merge_enabled and segments:
        if _merge_with_ffmpeg(segments, final_path):
            merge_status = "success"
            merge_note = "Merged clips with ffmpeg concat."
        else:
            final_path.write_text("DRY_RUN_OR_FFMPEG_MERGE_PLACEHOLDER\n" + "\n".join(str(seg.get("output_clip_path")) for seg in segments), encoding="utf-8")
            merge_note = "ffmpeg merge unavailable or source clips are placeholders; wrote merge placeholder for manifest continuity."
    merge_data = {
        "schema_version": SCHEMA_VERSION,
        "stage": "09D_final_merge_and_manifest_check",
        "status": "success" if segments else "needs_retry",
        "merge_status": merge_status,
        "merge_note": merge_note,
        "final_video_path": str(final_path),
        "final_audio_path": str(final_audio_path),
        "clip_count": len(segments),
        "expected_clip_count": len(plan.get("segments", []) or []),
        "missing_segments": resume.get("missing_segments", []),
    }
    path = output_dir / "merge_result.json"
    io_utils.write_json(path, merge_data)
    return {**merge_data, "merge_result_path": str(path)}


def run_video_stages(image_manifest: dict[str, Any], audio_timeline: dict[str, Any], final_audio_path: str | Path, output_dir: str | Path, storyboard: dict[str, Any] | None = None) -> dict[str, Any]:
    stage_status: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}
    outputs["09A"] = workflow_adapter.build_segment_plan(image_manifest, audio_timeline, final_audio_path, output_dir, storyboard=storyboard or {})
    io_utils.write_json(Path(output_dir) / "video_plan.json", outputs["09A"])
    stage_status.append(_run_and_score("09A", outputs["09A"], output_dir, "09A_video_segment_plan.json"))
    outputs["09B"] = run_09b(outputs["09A"], output_dir)
    stage_status.append(_run_and_score("09B", outputs["09B"], output_dir, "09B_ltx23_execution.json"))
    outputs["09C"] = run_09c(outputs["09A"], outputs["09B"], output_dir)
    stage_status.append(_run_and_score("09C", outputs["09C"], output_dir, "09C_resume_scan.json"))
    outputs["09D"] = run_09d(outputs["09A"], outputs["09C"], final_audio_path, output_dir)
    stage_status.append(_run_and_score("09D", outputs["09D"], output_dir, "09D_final_merge.json"))
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "video_execution", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(image_manifest: dict[str, Any], audio_timeline: dict[str, Any], final_audio_path: str | Path, config: dict[str, Any], stage_result: dict[str, Any], output_dir: str | Path, storyboard: dict[str, Any] | None = None) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a = outputs["09A"]
    b = outputs["09B"]
    c = outputs["09C"]
    d = outputs["09D"]
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result.get("stage_status", [])}
    failed = c.get("missing_segments", []) if isinstance(c.get("missing_segments"), list) else []
    retry_plan = {
        "needs_retry": bool(failed) or bool(b.get("failed_video_segments")),
        "retry_scope": "failed_video_segments_only" if failed or b.get("failed_video_segments") else "none",
        "failed_segment_ids": [item.get("segment_id") for item in failed if isinstance(item, dict)] + [item.get("segment_id") for item in b.get("failed_video_segments", []) if isinstance(item, dict)],
        "do_not_rerun_06_07_08": True,
        "notes": ["09 失败只重跑缺失视频段；除非 image_manifest/final_audio/audio_timeline 本身缺失，否则不回滚上游。"],
    }
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "09_video",
        "status": "success",
        "stage_mode": "video_execution",
        "execution_mode": a.get("execution_mode"),
        "window_mode": a.get("window_mode"),
        "window_size": a.get("window_size"),
        "stride": a.get("stride"),
        "source": {
            "required_upstream": ["07_storyboard_image.image_manifest.json", "08_audio.final_audio.wav", "08_audio.audio_timeline.json"],
            "optional_upstream": ["06_storyboard.storyboard.json"],
            "upstream_schema_versions": {"06": (storyboard or {}).get("schema_version"), "07": image_manifest.get("schema_version"), "08_timeline": audio_timeline.get("schema_version")},
            "output_dir": str(output_dir),
        },
        "final_audio_path": str(final_audio_path),
        "video_plan_path": str(Path(output_dir) / "video_plan.json"),
        "resume_manifest_path": c.get("resume_manifest_path"),
        "merge_result_path": d.get("merge_result_path"),
        "final_video_path": d.get("final_video_path"),
        "merge_status": d.get("merge_status"),
        "video_segments": c.get("segments", []),
        "execution_results": b.get("execution_results", []),
        "failed_video_segments": b.get("failed_video_segments", []),
        "retry_plan": retry_plan,
        "settings": a.get("settings", {}),
        "stage_status": stage_result.get("stage_status", []),
        "quality_report": {"needs_retry": retry_plan["needs_retry"], "stage_scores": stage_scores, "completed_count": c.get("completed_count"), "missing_count": c.get("missing_count")},
        "notes": [
            "09 采用滑动窗口关键帧方案：4图为 1-4、4-7、7-10；6图为 1-6、6-11；9图为 1-9、9-17。",
            "09 采用外部 Python 一段一提交，ComfyUI 每次只运行一组关键帧窗口。",
            "每段 ltx_prompt/negative_prompt/motion_policy 由 09 根据 06/07/08 自动生成并注入工作流。",
        ],
        "config": config,
    }
    validation = schema_validator.validate_final_output({**data, "schema_validation": {}})
    needs_review = retry_plan["needs_retry"] or any(item.get("status") != "success" for item in stage_result.get("stage_status", [])) or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
