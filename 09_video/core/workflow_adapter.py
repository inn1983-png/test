from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _safe_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _image_path_from_entry(entry: dict[str, Any]) -> str:
    for key in ("image_path", "output_path", "output_image_path", "path"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    execution = entry.get("execution_result") if isinstance(entry.get("execution_result"), dict) else {}
    value = execution.get("output_path")
    return value if isinstance(value, str) else ""


def collect_storyboard_images(image_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect ordered storyboard images from 07 image_manifest.

    07 may expose images under top-level images or nested image_manifest.images.
    This adapter keeps frame order stable and never invents frames.
    """
    raw_images = image_manifest.get("images")
    if not isinstance(raw_images, list):
        nested = image_manifest.get("image_manifest") if isinstance(image_manifest.get("image_manifest"), dict) else {}
        raw_images = nested.get("images") if isinstance(nested.get("images"), list) else []
    images: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_images, start=1):
        if not isinstance(item, dict):
            continue
        path = _image_path_from_entry(item)
        if not path:
            continue
        images.append(
            {
                "frame_id": item.get("frame_id") or f"frame_{idx:04d}",
                "sequence_index": _safe_int(item.get("sequence_index"), idx),
                "image_path": path,
                "source_status": item.get("status") or (item.get("execution_result") or {}).get("status"),
                "storyboard_ref": item.get("storyboard_ref") or item.get("task_id"),
                "positive_prompt": item.get("positive_prompt") or item.get("prompt") or "",
            }
        )
    images.sort(key=lambda item: (item.get("sequence_index") or 0, str(item.get("frame_id") or "")))
    return images


def _audio_duration_from_timeline(audio_timeline: dict[str, Any]) -> float:
    for key in ("duration_seconds", "total_duration_seconds", "duration"):
        value = _safe_float(audio_timeline.get(key), 0.0)
        if value > 0:
            return value
    entries = audio_timeline.get("entries") if isinstance(audio_timeline.get("entries"), list) else []
    max_end = 0.0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        max_end = max(max_end, _safe_float(entry.get("end_seconds") or entry.get("end"), 0.0))
    return max_end


def _timeline_text(entries: list[dict[str, Any]], start: float, end: float) -> str:
    parts: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        e_start = _safe_float(entry.get("start_seconds") or entry.get("start"), 0.0)
        e_end = _safe_float(entry.get("end_seconds") or entry.get("end"), e_start)
        if e_end < start or e_start > end:
            continue
        text = str(entry.get("text") or entry.get("content") or "").strip()
        speaker = str(entry.get("speaker") or entry.get("character") or entry.get("voice_id") or "").strip()
        line_type = str(entry.get("line_type") or entry.get("type") or "").strip()
        if text:
            prefix = f"{line_type}/{speaker}".strip("/")
            parts.append(f"[{max(e_start - start, 0):.1f}s] {prefix}: {text}" if prefix else f"[{max(e_start - start, 0):.1f}s] {text}")
    return " | ".join(parts)


def _frames_for_duration(duration: float, fps: float, formula: str) -> int:
    a = float(duration)
    b = float(fps)
    allowed = {"a": a, "b": b, "int": int, "round": round, "ceil": math.ceil, "floor": math.floor, "max": max, "min": min}
    try:
        result = int(eval(formula, {"__builtins__": {}}, allowed))  # noqa: S307 - controlled local formula env
    except Exception:
        result = int(a * b / 8) * 8 + 1
    return max(result, 9)


def build_segment_plan(image_manifest: dict[str, Any], audio_timeline: dict[str, Any], final_audio_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    images = collect_storyboard_images(image_manifest)
    if not images:
        raise RuntimeError("09_video requires 07_storyboard_image image_manifest with ordered images.")

    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    audio_slices_dir = output_dir / "audio_slices"
    clips_dir.mkdir(parents=True, exist_ok=True)
    audio_slices_dir.mkdir(parents=True, exist_ok=True)

    fps = _safe_float(os.getenv("AI_DRAMA_VIDEO_FPS", "24"), 24.0)
    duration = _safe_float(os.getenv("AI_DRAMA_VIDEO_SEGMENT_SECONDS", "10"), 10.0)
    if duration <= 0:
        duration = 10.0
    if os.getenv("AI_DRAMA_VIDEO_SEGMENT_SECONDS", "").strip() == "12":
        duration = 12.0
    overlap_frames = _safe_int(os.getenv("AI_DRAMA_VIDEO_OVERLAP_FRAMES", "0"), 0)
    width = _safe_int(os.getenv("AI_DRAMA_VIDEO_WIDTH", "1280"), 1280)
    height = _safe_int(os.getenv("AI_DRAMA_VIDEO_HEIGHT", "720"), 720)
    mode = os.getenv("AI_DRAMA_VIDEO_EXECUTION_MODE", "dry_run").strip().lower()
    frames_formula = os.getenv("AI_DRAMA_VIDEO_FRAMES_FORMULA", "int(a*b/8)*8+1")
    total_duration = _audio_duration_from_timeline(audio_timeline)
    if total_duration <= 0:
        total_duration = duration
    segment_count = max(1, math.ceil(total_duration / duration))
    entries = audio_timeline.get("entries") if isinstance(audio_timeline.get("entries"), list) else []

    segments: list[dict[str, Any]] = []
    for index in range(1, segment_count + 1):
        start = round((index - 1) * duration, 3)
        end = round(min(index * duration, total_duration), 3)
        actual_duration = max(0.001, end - start)
        image = images[(index - 1) % len(images)]
        clip_name = f"clip_{index:04d}.mp4"
        slice_name = f"audio_slice_{index:04d}.wav"
        prompt = _timeline_text(entries, start, end)
        segments.append(
            {
                "segment_id": f"video_seg_{index:04d}",
                "segment_index": index,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": actual_duration,
                "fps": fps,
                "width": width,
                "height": height,
                "frame_count": _frames_for_duration(actual_duration, fps, frames_formula),
                "overlap_frames": overlap_frames,
                "source_image": image,
                "image_path": image["image_path"],
                "audio_source_path": str(final_audio_path),
                "audio_slice_path": str(audio_slices_dir / slice_name),
                "output_clip_path": str(clips_dir / clip_name),
                "output_basename": Path(clip_name).stem,
                "timeline_text": prompt,
                "ltx_prompt": build_ltx_prompt(prompt),
                "execution_mode": "execute" if mode in {"execute", "comfyui", "real"} else "dry_run",
            }
        )
    return {
        "stage": "09A_segment_plan",
        "status": "success",
        "execution_mode": "execute" if mode in {"execute", "comfyui", "real"} else "dry_run",
        "final_audio_path": str(final_audio_path),
        "image_count": len(images),
        "audio_duration_seconds": total_duration,
        "segment_seconds": duration,
        "segment_count": len(segments),
        "segments": segments,
        "settings": {
            "fps": fps,
            "width": width,
            "height": height,
            "frames_formula": frames_formula,
            "overlap_frames": overlap_frames,
            "workflow_path": os.getenv("AI_DRAMA_VIDEO_COMFYUI_WORKFLOW", os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", "")),
            "based_on_ltx23_audio_slice_workflow": True,
        },
    }


def build_ltx_prompt(timeline_text: str) -> str:
    base = os.getenv(
        "AI_DRAMA_VIDEO_PROMPT_TEMPLATE",
        "Use the reference storyboard image as the exact visual anchor. Animate only subtle character motion, natural breathing, small facial changes, cloth movement, and a stable camera. Keep scene, identity, costume, props, lighting, and composition consistent. Match the provided audio segment timing. No subtitles, no captions, no typography, no watermark.",
    )
    if timeline_text:
        return f"{base} Audio/acting beats: {timeline_text}"
    return base


def build_comfyui_workflow_payload(segment: dict[str, Any]) -> dict[str, Any]:
    """Return logical values that should be injected into the verified LTX2.3 workflow.

    The uploaded reference workflow uses project_name/base_path/duration/current_chunk,
    image inputs, audio slicing, ResumeScanner, VideoSaveMerge and final merge nodes.
    This adapter exposes those values by stable semantic names; concrete node ids are
    mapped by ComfyUIClient from environment variables.
    """
    return {
        "segment_id": segment.get("segment_id"),
        "current_segment_index": segment.get("segment_index"),
        "project_name": os.getenv("AI_DRAMA_VIDEO_PROJECT_NAME", "ai_drama_project"),
        "base_path": os.getenv("AI_DRAMA_VIDEO_BASE_PATH", str(Path(segment.get("output_clip_path", ".")).parent.parent)),
        "audio_path": segment.get("audio_source_path"),
        "image_path": segment.get("image_path"),
        "prompt": segment.get("ltx_prompt"),
        "duration": segment.get("duration_seconds"),
        "fps": segment.get("fps"),
        "width": segment.get("width"),
        "height": segment.get("height"),
        "frame_count": segment.get("frame_count"),
        "overlap_frames": segment.get("overlap_frames", 0),
        "output_clip_path": segment.get("output_clip_path"),
        "output_basename": segment.get("output_basename"),
    }
