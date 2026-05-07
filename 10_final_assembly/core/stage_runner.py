from __future__ import annotations

import os
import shutil
from importlib import import_module
from pathlib import Path
from typing import Any

io_utils = import_module("00_common.io_utils")
stage_status_writer = import_module("00_common.stage_status")
ffmpeg_client = import_module("10_final_assembly.core.ffmpeg_client")
quality_checker = import_module("10_final_assembly.core.quality_checker")
schema_validator = import_module("10_final_assembly.core.schema_validator")

SCHEMA_VERSION = "1.1"
MIN_VALID_FINAL_BYTES = int(os.getenv("AI_DRAMA_FINAL_MIN_VALID_BYTES", "1024"))

STAGES: list[dict[str, str]] = [
    {"stage_id": "10A", "name": "input_check", "output_file": "10A_input_check.json"},
    {"stage_id": "10B", "name": "video_prepare", "output_file": "10B_video_prepare.json"},
    {"stage_id": "10C", "name": "audio_subtitle_align", "output_file": "10C_audio_subtitle_align.json"},
    {"stage_id": "10D", "name": "final_export", "output_file": "10D_final_export.json"},
]
STAGE_BY_ID = {stage["stage_id"]: stage for stage in STAGES}


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
    status = "success" if quality["passed"] else "needs_review"
    stage = STAGE_BY_ID.get(stage_id, {"name": stage_id})
    stage_status_writer.mark_stage_finished(
        "10_final_assembly",
        output_dir,
        stage_id,
        stage["name"],
        status,
        output_file=output_path,
        score=quality.get("score"),
        issues_count=len(quality.get("issues", []) or []),
    )
    return {"stage_id": stage_id, "status": status, "output_path": output_path, "quality": quality}


def _mark_started(stage_id: str, output_dir: str | Path) -> None:
    stage = STAGE_BY_ID.get(stage_id, {"name": stage_id})
    stage_status_writer.mark_stage_started("10_final_assembly", output_dir, stage_id, stage["name"], "stage started")


def _valid_media(path: Path | None, min_bytes: int = MIN_VALID_FINAL_BYTES) -> bool:
    if path is None:
        return False
    return ffmpeg_client.is_probably_valid_media(path, min_bytes=min_bytes)


def _as_path(value: Any, base_dir: Path | None = None) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.exists():
        return path
    if base_dir:
        candidate = base_dir / value
        if candidate.exists():
            return candidate
    return path


def _collect_clip_paths(video_manifest: dict[str, Any], video_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for key in ("video_segments", "segments", "clips"):
        rows = video_manifest.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = row.get("output_clip_path") or row.get("clip_path") or row.get("path")
            path = _as_path(value, video_dir)
            if path and _valid_media(path):
                candidates.append(path)
    if not candidates:
        clips_dir = video_dir / "clips"
        if clips_dir.exists():
            candidates = sorted([p for p in clips_dir.glob("*.mp4") if _valid_media(p)])
    return candidates


def run_10a(video_manifest: dict[str, Any], paths: dict[str, Path], output_dir: str | Path) -> dict[str, Any]:
    video_dir = paths["video_dir"]
    audio_dir = paths["audio_dir"]
    preferred_from_manifest = _as_path(video_manifest.get("final_video_path"), video_dir)
    preferred_from_convention = video_dir / "final_video.mp4"
    preferred_video = preferred_from_manifest if _valid_media(preferred_from_manifest) else preferred_from_convention
    if not _valid_media(preferred_video):
        preferred_video = None
    clip_paths = _collect_clip_paths(video_manifest, video_dir)
    subtitle_srt = audio_dir / "subtitle.srt"
    subtitle_ass = audio_dir / "subtitle.ass"
    data = {
        "schema_version": SCHEMA_VERSION,
        "stage": "10A_input_check",
        "status": "success" if paths["video_manifest_path"].exists() and paths["final_audio_path"].exists() and (preferred_video or clip_paths) else "needs_review",
        "video_manifest_path": str(paths["video_manifest_path"]),
        "video_dir": str(video_dir),
        "audio_dir": str(audio_dir),
        "final_audio_path": str(paths["final_audio_path"]),
        "preferred_video_path": str(preferred_video) if preferred_video else None,
        "clip_paths": [str(p) for p in clip_paths],
        "subtitle_candidates": {"srt": str(subtitle_srt) if subtitle_srt.exists() else None, "ass": str(subtitle_ass) if subtitle_ass.exists() else None},
        "input_policy": {
            "video_priority": ["09_video/final_video.mp4", "09_video/video_segments clips"],
            "audio_priority": ["08_audio/final_audio.wav"],
            "subtitles": ["08_audio/subtitle.srt", "08_audio/subtitle.ass"],
        },
    }
    return data


def run_10b(check: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    prepared_dir = output_dir / "prepared"
    io_utils.ensure_dir(prepared_dir)
    prepared_video = prepared_dir / "prepared_video.mp4"
    client = ffmpeg_client.FFmpegClient()
    dry_run = os.getenv("AI_DRAMA_FINAL_DRY_RUN", "0").strip().lower() in {"1", "true", "yes", "on"}

    preferred = _as_path(check.get("preferred_video_path"))
    if preferred and _valid_media(preferred) and not dry_run:
        shutil.copy2(preferred, prepared_video)
        probe = ffmpeg_client.ffprobe_validate(prepared_video)
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": "10B_video_prepare",
            "status": "success",
            "video_source_mode": "final_video",
            "prepared_video_path": str(prepared_video),
            "source_video_path": str(preferred),
            "ffmpeg_result": None,
            "ffprobe_validation": probe,
        }

    clip_paths = [_as_path(p) for p in check.get("clip_paths", []) or []]
    clip_paths = [p for p in clip_paths if p and _valid_media(p)]
    if clip_paths and not dry_run:
        result = client.concat_clips(clip_paths, prepared_video)
        if result.get("status") == "success" and _valid_media(prepared_video):
            probe = ffmpeg_client.ffprobe_validate(prepared_video)
            return {
                "schema_version": SCHEMA_VERSION,
                "stage": "10B_video_prepare",
                "status": "success",
                "video_source_mode": "concat_clips",
                "prepared_video_path": str(prepared_video),
                "source_clip_paths": [str(p) for p in clip_paths],
                "ffmpeg_result": result,
                "ffprobe_validation": probe,
            }

    prepared_video.write_text("DRY_RUN_FINAL_ASSEMBLY_PREPARED_VIDEO_PLACEHOLDER\n", encoding="utf-8")
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "10B_video_prepare",
        "status": "needs_review" if not dry_run else "success",
        "video_source_mode": "dry_run_placeholder",
        "prepared_video_path": str(prepared_video),
        "source_video_path": str(preferred) if preferred else None,
        "source_clip_paths": [str(p) for p in clip_paths],
        "ffmpeg_available": client.available,
        "dry_run": dry_run,
        "notes": ["无可用 ffmpeg 或处于 dry_run 时，写入可检查占位 prepared_video.mp4。"],
    }


def run_10c(check: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    subtitle_dir = output_dir / "subtitles"
    io_utils.ensure_dir(subtitle_dir)
    final_audio_path = _as_path(check.get("final_audio_path"))
    copied: list[dict[str, str]] = []
    missing: list[str] = []
    for name in ("subtitle.srt", "subtitle.ass"):
        src = Path(check.get("audio_dir", "")) / name
        if src.exists():
            dst = subtitle_dir / name
            shutil.copy2(src, dst)
            copied.append({"name": name, "source_path": str(src), "output_path": str(dst)})
        else:
            missing.append(str(src))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "10C_audio_subtitle_align",
        "status": "success" if final_audio_path and final_audio_path.exists() else "needs_review",
        "final_audio_path": str(final_audio_path) if final_audio_path else None,
        "audio_policy": "08_audio/final_audio.wav is authoritative final audio.",
        "copied_subtitles": copied,
        "missing_subtitles": missing,
        "subtitle_policy": {"default_burn_subtitles": False, "burn_env": "AI_DRAMA_FINAL_BURN_SUBTITLES=1", "copy_only_by_default": True},
    }


def run_10d(video_prepare: dict[str, Any], audio_subtitle: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    final_path = output_dir / "final.mp4"
    force = os.getenv("AI_DRAMA_FINAL_FORCE_RERUN", "0").strip().lower() in {"1", "true", "yes", "on"}
    dry_run = os.getenv("AI_DRAMA_FINAL_DRY_RUN", "0").strip().lower() in {"1", "true", "yes", "on"}
    burn = os.getenv("AI_DRAMA_FINAL_BURN_SUBTITLES", "0").strip().lower() in {"1", "true", "yes", "on"}

    if _valid_media(final_path) and not force:
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": "10D_final_export",
            "status": "skipped",
            "export_mode": "skip_existing",
            "final_video_path": str(final_path),
            "skip_reason": "final.mp4 already exists and is valid; set AI_DRAMA_FINAL_FORCE_RERUN=1 to re-export.",
        }

    client = ffmpeg_client.FFmpegClient()
    prepared = _as_path(video_prepare.get("prepared_video_path"))
    audio = _as_path(audio_subtitle.get("final_audio_path"))
    if dry_run or not prepared or not audio or not client.available:
        final_path.write_text(
            "DRY_RUN_FINAL_ASSEMBLY_PLACEHOLDER\n"
            f"prepared_video={prepared}\n"
            f"final_audio={audio}\n"
            f"burn_subtitles={burn}\n",
            encoding="utf-8",
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "stage": "10D_final_export",
            "status": "success" if dry_run else "needs_review",
            "export_mode": "dry_run_placeholder",
            "final_video_path": str(final_path),
            "ffmpeg_available": client.available,
            "dry_run": dry_run,
        }

    muxed_path = output_dir / "final_muxed.mp4" if burn else final_path
    mux_result = client.mux_video_audio(prepared, audio, muxed_path)
    burn_result = None
    export_mode = "mux"
    if mux_result.get("status") == "success" and burn:
        copied = audio_subtitle.get("copied_subtitles", []) if isinstance(audio_subtitle.get("copied_subtitles"), list) else []
        subtitle_path = None
        for row in copied:
            if isinstance(row, dict) and row.get("name") == "subtitle.ass":
                subtitle_path = _as_path(row.get("output_path"))
                break
        if subtitle_path is None:
            for row in copied:
                if isinstance(row, dict) and row.get("name") == "subtitle.srt":
                    subtitle_path = _as_path(row.get("output_path"))
                    break
        if subtitle_path and subtitle_path.exists():
            burn_result = client.burn_subtitles(muxed_path, subtitle_path, final_path)
            export_mode = "burn_subtitles"
        else:
            burn_result = {"status": "failed", "stderr": "burn requested but no copied subtitle found"}

    ok = _valid_media(final_path)
    probe = None
    if ok:
        probe = ffmpeg_client.ffprobe_validate(final_path)
        if not probe.get("valid"):
            ok = False
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "10D_final_export",
        "status": "success" if ok else "needs_review",
        "export_mode": export_mode,
        "final_video_path": str(final_path),
        "mux_result": mux_result,
        "burn_result": burn_result,
        "burn_subtitles": burn,
        "ffprobe_validation": probe,
    }


def run_final_assembly_stages(video_manifest: dict[str, Any], paths: dict[str, Path], output_dir: str | Path) -> dict[str, Any]:
    stage_status: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}
    _mark_started("10A", output_dir)
    outputs["10A"] = run_10a(video_manifest, paths, output_dir)
    stage_status.append(_run_and_score("10A", outputs["10A"], output_dir, "10A_input_check.json"))
    _mark_started("10B", output_dir)
    outputs["10B"] = run_10b(outputs["10A"], output_dir)
    stage_status.append(_run_and_score("10B", outputs["10B"], output_dir, "10B_video_prepare.json"))
    _mark_started("10C", output_dir)
    outputs["10C"] = run_10c(outputs["10A"], output_dir)
    stage_status.append(_run_and_score("10C", outputs["10C"], output_dir, "10C_audio_subtitle_align.json"))
    _mark_started("10D", output_dir)
    outputs["10D"] = run_10d(outputs["10B"], outputs["10C"], output_dir)
    stage_status.append(_run_and_score("10D", outputs["10D"], output_dir, "10D_final_export.json"))
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "final_assembly", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(video_manifest: dict[str, Any], paths: dict[str, Path], config: dict[str, Any], stage_result: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    outputs = stage_result["outputs"]
    a = outputs["10A"]
    b = outputs["10B"]
    c = outputs["10C"]
    d = outputs["10D"]
    final_manifest_path = output_dir / "final_manifest.json"
    final_meta_path = output_dir / "final_meta.json"
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result.get("stage_status", [])}
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "10_final_assembly",
        "status": "success",
        "stage_mode": "final_assembly",
        "uses_llm": False,
        "uses_ltx": False,
        "generates_new_video_segments": False,
        "final_video_path": d.get("final_video_path"),
        "final_manifest_path": str(final_manifest_path),
        "final_meta_path": str(final_meta_path),
        "video_manifest_path": str(paths["video_manifest_path"]),
        "final_audio_path": str(paths["final_audio_path"]),
        "source": {
            "required_upstream": ["09_video/video_manifest.json", "08_audio/final_audio.wav"],
            "optional_upstream": ["09_video/final_video.mp4", "09_video/clips/*.mp4", "08_audio/subtitle.srt", "08_audio/subtitle.ass"],
            "video_source_mode": b.get("video_source_mode"),
            "source_video_path": b.get("source_video_path"),
            "source_clip_paths": b.get("source_clip_paths", []),
            "audio_source": "08_audio/final_audio.wav",
        },
        "subtitle_policy": {
            "default_burn_subtitles": False,
            "burn_subtitles": bool(d.get("burn_subtitles", False)),
            "copied_subtitles": c.get("copied_subtitles", []),
            "missing_subtitles": c.get("missing_subtitles", []),
        },
        "export": d,
        "stage_status": stage_result.get("stage_status", []),
        "quality_report": {"stage_scores": stage_scores},
        "settings": {
            "dry_run": os.getenv("AI_DRAMA_FINAL_DRY_RUN", "0"),
            "force_rerun": os.getenv("AI_DRAMA_FINAL_FORCE_RERUN", "0"),
            "burn_subtitles": os.getenv("AI_DRAMA_FINAL_BURN_SUBTITLES", "0"),
            "ffmpeg": os.getenv("AI_DRAMA_FFMPEG", "ffmpeg"),
        },
        "upstream_video_manifest_status": video_manifest.get("status"),
        "config": config,
        "notes": [
            "10 是最终包装层：不调用 LLM、不调用 LTX、不生成新视频片段。",
            "默认只复制字幕，不烧录字幕；设置 AI_DRAMA_FINAL_BURN_SUBTITLES=1 后才尝试烧录。",
            "final.mp4 已存在且有效时默认跳过；设置 AI_DRAMA_FINAL_FORCE_RERUN=1 可强制重导出。",
            "公开剪辑项目建议作为后续插件接入，默认路径保持 FFmpeg 确定性封装。",
        ],
    }
    validation = schema_validator.validate_final_output({**data, "schema_validation": {}})
    needs_review = any(item.get("status") != "success" for item in stage_result.get("stage_status", [])) or not validation["passed"] or d.get("status") == "needs_review"
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
