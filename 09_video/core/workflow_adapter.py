from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any


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
                "positive_prompt": item.get("positive_prompt") or item.get("prompt") or "",
            }
        )
    images.sort(key=lambda item: (item.get("sequence_index") or 0, str(item.get("frame_id") or "")))
    return images


def _storyboard_frame_index(storyboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frames = storyboard.get("frames") if isinstance(storyboard.get("frames"), list) else []
    index: dict[str, dict[str, Any]] = {}
    for idx, frame in enumerate(frames, start=1):
        if not isinstance(frame, dict):
            continue
        frame_id = str(frame.get("frame_id") or frame.get("id") or f"frame_{idx:04d}")
        seq = _safe_int(frame.get("sequence_index"), idx)
        index[frame_id] = frame
        index[f"__seq__{seq}"] = frame
    return index


def _frame_detail(image: dict[str, Any], frame_index: dict[str, dict[str, Any]], fallback_number: int) -> dict[str, Any]:
    frame_id = str(image.get("frame_id") or f"frame_{fallback_number:04d}")
    seq = _safe_int(image.get("sequence_index"), fallback_number)
    frame = frame_index.get(frame_id) or frame_index.get(f"__seq__{seq}") or {}
    return {
        "frame_id": frame_id,
        "sequence_index": seq,
        "image_path": image.get("image_path"),
        "story_action": str(frame.get("story_action") or frame.get("action") or frame.get("visual_action") or image.get("positive_prompt") or "hold the visual state shown in this keyframe").strip(),
        "emotion": str(frame.get("emotion") or frame.get("character_emotion") or frame.get("emotional_tone") or "controlled, natural acting").strip(),
        "camera_plan": str(frame.get("camera_plan") or frame.get("camera") or frame.get("shot_type") or "stable cinematic camera").strip(),
        "composition_notes": str(frame.get("composition_notes") or frame.get("composition") or "keep the same composition from the storyboard image").strip(),
        "continuity_notes": str(frame.get("continuity_notes") or frame.get("continuity") or "continue smoothly without changing identity, costume, scene, props, lighting, or layout").strip(),
    }


def _audio_duration_from_timeline(audio_timeline: dict[str, Any]) -> float:
    for key in ("duration_seconds", "total_duration_seconds", "duration"):
        value = _safe_float(audio_timeline.get(key), 0.0)
        if value > 0:
            return value
    entries = audio_timeline.get("entries") if isinstance(audio_timeline.get("entries"), list) else []
    max_end = 0.0
    for entry in entries:
        if isinstance(entry, dict):
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


def _frames_for_duration(duration: float, fps: float) -> int:
    raw = int(float(duration) * float(fps) / 8) * 8 + 1
    return max(raw, 9)


def _window_mode() -> tuple[int, int, str]:
    raw = os.getenv("AI_DRAMA_VIDEO_KEYFRAME_WINDOW", os.getenv("AI_DRAMA_VIDEO_IMAGE_GROUP_SIZE", "4")).strip().lower()
    if raw in {"4", "4grid", "4图", "four"}:
        return 4, 3, "4grid"
    if raw in {"6", "6grid", "6图", "six"}:
        return 6, 5, "6grid"
    if raw in {"9", "9grid", "9图", "nine"}:
        return 9, 8, "9grid"
    size = max(2, _safe_int(raw, 4))
    return size, max(1, size - 1), f"{size}grid"


def _build_windows(images: list[dict[str, Any]], window_size: int, stride: int) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    start = 0
    while start < len(images):
        window = images[start : start + window_size]
        if len(window) < window_size:
            window = [*window, *([images[-1]] * (window_size - len(window)))]
        windows.append(window)
        if start + window_size >= len(images):
            break
        start += stride
    return windows


def build_negative_prompt() -> str:
    return os.getenv(
        "AI_DRAMA_VIDEO_NEGATIVE_PROMPT",
        "subtitles, captions, text, typography, watermark, logo, extra characters, new person, face change, identity change, costume change, scene change, prop change, modern objects, modern clothes, wrong era, cartoon, anime, 3d render, low quality, blurry, distorted face, bad hands, extra limbs, deformed body, flicker, camera shake",
    )


def build_motion_policy(window_size: int) -> dict[str, Any]:
    return {
        "policy": "window_keyframe_progression",
        "window_size": window_size,
        "motion_strength": os.getenv("AI_DRAMA_VIDEO_MOTION_STRENGTH", "low"),
        "identity_lock": True,
        "face_lock": True,
        "costume_lock": True,
        "scene_lock": True,
        "prop_lock": True,
        "lighting_lock": True,
        "composition_lock": True,
        "allowed_motion": ["natural breathing", "subtle facial expression", "small hand movement", "cloth movement", "gentle camera push-in", "smooth transition between provided keyframes"],
        "forbidden_changes": ["new characters", "face change", "costume change", "scene change", "new props", "subtitles", "watermark", "modern objects"],
    }


def build_window_ltx_prompt(frame_details: list[dict[str, Any]], timeline_text: str) -> str:
    base = os.getenv(
        "AI_DRAMA_VIDEO_PROMPT_TEMPLATE",
        "Use the provided storyboard keyframe image group as the exact visual anchor. Animate a smooth progression across the keyframes. Keep the same character identity, face, costume, scene, props, lighting, composition style, and historical era. Only allow subtle natural motion: breathing, small facial expression changes, slight hand movement, cloth movement, and gentle camera movement. Do not add new characters or props. Do not change face, costume, scene, layout, or era. No subtitles, no captions, no typography, no watermark.",
    )
    lines = [base, "", "Keyframe progression:"]
    for idx, frame in enumerate(frame_details, start=1):
        lines.append(f"{idx}. {frame.get('story_action')} | emotion: {frame.get('emotion')} | camera: {frame.get('camera_plan')}")
    continuity = "; ".join(str(frame.get("continuity_notes") or "").strip() for frame in frame_details if frame.get("continuity_notes"))
    if continuity:
        lines.extend(["", f"Continuity: {continuity}"])
    if timeline_text:
        lines.extend(["", f"Audio acting beats: {timeline_text}"])
    return "\n".join(lines).strip()


def build_segment_plan(
    image_manifest: dict[str, Any],
    audio_timeline: dict[str, Any],
    final_audio_path: str | Path,
    output_dir: str | Path,
    storyboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    total_duration = _audio_duration_from_timeline(audio_timeline)
    if total_duration <= 0:
        total_duration = duration
    entries = audio_timeline.get("entries") if isinstance(audio_timeline.get("entries"), list) else []
    window_size, stride, window_mode = _window_mode()
    windows = _build_windows(images, window_size, stride)
    audio_segment_count = max(1, math.ceil(total_duration / duration))
    segment_count = max(audio_segment_count, len(windows))
    frame_index = _storyboard_frame_index(storyboard or {})
    negative_prompt = build_negative_prompt()

    segments: list[dict[str, Any]] = []
    for index in range(1, segment_count + 1):
        start = round((index - 1) * duration, 3)
        end = round(min(index * duration, total_duration), 3)
        actual_duration = max(0.001, end - start)
        window = windows[(index - 1) % len(windows)]
        frame_details = [_frame_detail(image, frame_index, fallback_number=i) for i, image in enumerate(window, start=1)]
        image_paths = [str(frame.get("image_path") or "") for frame in frame_details]
        frame_ids = [str(frame.get("frame_id") or f"frame_{i:04d}") for i, frame in enumerate(frame_details, start=1)]
        clip_name = f"clip_{index:04d}.mp4"
        slice_name = f"audio_slice_{index:04d}.wav"
        timeline_text = _timeline_text(entries, start, end)
        segments.append(
            {
                "segment_id": f"video_seg_{index:04d}",
                "segment_index": index,
                "window_mode": window_mode,
                "window_size": window_size,
                "stride": stride,
                "frame_ids": frame_ids,
                "image_paths": image_paths,
                "keyframe_details": frame_details,
                "anchor_frame_id": frame_ids[-1] if frame_ids else None,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": actual_duration,
                "fps": fps,
                "width": width,
                "height": height,
                "frame_count": _frames_for_duration(actual_duration, fps),
                "overlap_frames": overlap_frames,
                "audio_source_path": str(final_audio_path),
                "audio_slice_path": str(audio_slices_dir / slice_name),
                "output_clip_path": str(clips_dir / clip_name),
                "output_basename": Path(clip_name).stem,
                "timeline_text": timeline_text,
                "ltx_prompt": build_window_ltx_prompt(frame_details, timeline_text),
                "negative_prompt": negative_prompt,
                "motion_policy": build_motion_policy(window_size),
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
        "window_mode": window_mode,
        "window_size": window_size,
        "stride": stride,
        "windows": [
            {"window_index": idx, "frame_ids": [str(img.get("frame_id")) for img in window], "image_paths": [str(img.get("image_path")) for img in window]}
            for idx, window in enumerate(windows, start=1)
        ],
        "segments": segments,
        "settings": {
            "fps": fps,
            "width": width,
            "height": height,
            "overlap_frames": overlap_frames,
            "workflow_path": os.getenv("AI_DRAMA_VIDEO_COMFYUI_WORKFLOW", os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", "")),
            "based_on_ltx23_audio_slice_workflow": True,
            "external_python_one_submit_per_window": True,
        },
    }


def build_comfyui_workflow_payload(segment: dict[str, Any]) -> dict[str, Any]:
    image_paths = [str(item) for item in (segment.get("image_paths") or []) if item]
    payload: dict[str, Any] = {
        "segment_id": segment.get("segment_id"),
        "current_segment_index": segment.get("segment_index"),
        "current_chunk": segment.get("segment_index"),
        "project_name": os.getenv("AI_DRAMA_VIDEO_PROJECT_NAME", "ai_drama_project"),
        "base_path": os.getenv("AI_DRAMA_VIDEO_BASE_PATH", str(Path(segment.get("output_clip_path", ".")).parent.parent)),
        "audio_path": segment.get("audio_source_path"),
        "prompt": segment.get("ltx_prompt"),
        "negative_prompt": segment.get("negative_prompt"),
        "duration": segment.get("duration_seconds"),
        "fps": segment.get("fps"),
        "width": segment.get("width"),
        "height": segment.get("height"),
        "frame_count": segment.get("frame_count"),
        "overlap_frames": segment.get("overlap_frames", 0),
        "window_size": segment.get("window_size"),
        "stride": segment.get("stride"),
        "output_clip_path": segment.get("output_clip_path"),
        "output_basename": segment.get("output_basename"),
        "image_paths": image_paths,
        "image_path": image_paths[0] if image_paths else None,
    }
    for idx in range(1, 10):
        payload[f"image_{idx}"] = image_paths[idx - 1] if idx <= len(image_paths) else ""
    return payload
