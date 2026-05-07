from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

ALLOWED_STABLE_MOTION = [
    "slow push in",
    "subtle breathing",
    "slight cloth movement",
    "candle flicker",
    "snow/rain/fog movement",
    "slow eye movement",
    "slight head turn",
    "hand grip close-up",
    "static confrontation",
    "reaction close-up",
    "insert shot",
]

FORBIDDEN_DIRECT_MOTION = [
    "running",
    "fighting",
    "hugging with body movement",
    "spinning camera",
    "large body turn",
    "multi-person physical interaction",
    "complex hand action",
    "fast camera movement",
]

STABILIZATION_RULES = [
    {
        "source_action": "抓住手腕",
        "keywords": ["抓住手腕", "抓腕", "攥住手腕", "grab wrist", "grabbing wrist", "wrist grab"],
        "stabilized_action": "wrist close-up / static confrontation / fingers tightening (手腕特写 / 两人对峙 / 手指收紧)",
        "forbidden_motion": ["complex hand action", "multi-person physical interaction"],
        "reason": "Wrist grabbing is converted into close-up and confrontation beats to avoid complex hand/body contact.",
    },
    {
        "source_action": "奔跑追逐",
        "keywords": ["奔跑追逐", "追逐", "奔跑", "逃跑", "跑向", "chase", "pursuit", "running", "run after"],
        "stabilized_action": "held wide shot + cloth moved by wind + slow push in (远景定格 + 衣摆风动 + 镜头缓推)",
        "forbidden_motion": ["running", "fast camera movement"],
        "reason": "Running or chasing is converted into a held wide composition with environmental motion and a slow camera move.",
    },
    {
        "source_action": "打斗",
        "keywords": ["打斗", "打架", "搏斗", "厮打", "交手", "fight", "fighting", "combat", "brawl"],
        "stabilized_action": "weapon insert shot + eye contact + broken prop detail (武器特写 + 眼神 + 破碎道具)",
        "forbidden_motion": ["fighting", "multi-person physical interaction", "complex hand action"],
        "reason": "Fighting is converted into inserts and reaction details instead of direct physical action.",
    },
    {
        "source_action": "拥抱",
        "keywords": ["拥抱", "抱住", "相拥", "hug", "hugging", "embrace", "embracing"],
        "stabilized_action": "static close-up + slight shoulder/back breathing (静态近景 + 肩背轻微起伏)",
        "forbidden_motion": ["hugging with body movement", "multi-person physical interaction"],
        "reason": "Hugging is converted into a mostly static close-up with minimal breathing movement.",
    },
    {
        "source_action": "争吵",
        "keywords": ["争吵", "吵架", "争执", "争辩", "怒吼", "argue", "arguing", "argument", "quarrel", "shout", "yell"],
        "stabilized_action": "alternating close-ups + oppressive eye contact (交替特写 + 眼神压迫)",
        "forbidden_motion": ["fast camera movement", "large body turn"],
        "reason": "Arguing is converted into close-up reactions and eye pressure instead of broad body movement.",
    },
    {
        "source_action": "转身离开",
        "keywords": ["转身离开", "转身", "离开", "背过身", "turn away", "turns away", "walk away", "leaves"],
        "stabilized_action": "held back view + slight cloth movement (背影定格 + 衣摆轻动)",
        "forbidden_motion": ["large body turn", "fast camera movement"],
        "reason": "Turning away is converted into a held back-view composition with only cloth movement.",
    },
]

_FORBIDDEN_KEYWORDS = {
    "running": ["running", "run", "奔跑", "追逐", "逃跑"],
    "fighting": ["fighting", "fight", "打斗", "打架", "搏斗"],
    "hugging with body movement": ["hugging", "hug", "拥抱", "抱住"],
    "spinning camera": ["spinning camera", "camera spin", "旋转镜头", "镜头旋转"],
    "large body turn": ["large body turn", "turn around", "转身", "大幅转身"],
    "multi-person physical interaction": ["multi-person physical interaction", "physical interaction", "多人肢体互动", "肢体互动"],
    "complex hand action": ["complex hand action", "hand action", "复杂手部动作", "抓住手腕", "抓腕"],
    "fast camera movement": ["fast camera movement", "quick camera", "rapid camera", "快速镜头", "镜头快速"],
}


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


def _edit_rhythm_entries(edit_rhythm: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(edit_rhythm, dict):
        return []
    entries = edit_rhythm.get("segments")
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _edit_rhythm_text(entries: list[dict[str, Any]], start: float, end: float) -> str:
    parts: list[str] = []
    for entry in entries:
        e_start = _safe_float(entry.get("start"), 0.0)
        e_end = _safe_float(entry.get("end"), e_start)
        if e_end < start or e_start > end:
            continue
        role = str(entry.get("suggested_visual_role") or "").strip()
        intensity = entry.get("intensity")
        pause = "pause" if entry.get("needs_visual_pause") else "no_pause"
        text = str(entry.get("text") or "").strip()
        label = "/".join(part for part in [role, f"intensity={intensity}" if intensity is not None else "", pause] if part)
        parts.append(f"[{max(e_start - start, 0):.1f}s] {label}: {text}" if label else f"[{max(e_start - start, 0):.1f}s] {text}")
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


def _build_windows(images: list[dict[str, Any]], window_size: int, stride: int) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    start = 0
    while start < len(images):
        original_window = images[start : start + window_size]
        padded_count = max(0, window_size - len(original_window))
        window = [*original_window, *([images[-1]] * padded_count)]
        windows.append({"items": window, "is_padded_window": padded_count > 0, "padded_frame_count": padded_count})
        if start + window_size >= len(images):
            break
        start += stride
    return windows


def _segment_role(index: int, total: int) -> str:
    if total <= 1:
        return "single"
    if index == 1:
        return "first"
    if index == total:
        return "last"
    return "middle"


def build_negative_prompt() -> str:
    return os.getenv(
        "AI_DRAMA_VIDEO_NEGATIVE_PROMPT",
        "subtitles, captions, text, typography, watermark, logo, extra characters, new person, face change, identity change, costume change, scene change, prop change, modern objects, modern clothes, wrong era, cartoon, anime, 3d render, low quality, blurry, distorted face, bad hands, extra limbs, deformed body, flicker, camera shake",
    )


def _dedupe_text(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _keyword_matches(text_lower: str, keyword: str) -> bool:
    needle = str(keyword or "").strip().lower()
    if not needle:
        return False
    if all(ord(ch) < 128 for ch in needle):
        return re.search(rf"\b{re.escape(needle)}\b", text_lower) is not None
    return needle in text_lower


def stabilize_action(action: str) -> dict[str, Any]:
    original = str(action or "").strip() or "hold the visual state shown in this keyframe"
    text_lower = original.lower()
    matched_rules = [
        rule
        for rule in STABILIZATION_RULES
        if any(_keyword_matches(text_lower, keyword) for keyword in rule.get("keywords", []))
    ]
    if matched_rules:
        return {
            "original_action": original,
            "stabilized_action": "; ".join(_dedupe_text([rule.get("stabilized_action") for rule in matched_rules])),
            "stabilization_reason": " ".join(_dedupe_text([rule.get("reason") for rule in matched_rules])),
            "matched_rules": [rule.get("source_action") for rule in matched_rules],
            "forbidden_match": _dedupe_text(
                [motion for rule in matched_rules for motion in (rule.get("forbidden_motion") or [])]
            ),
        }

    forbidden_match = [
        motion
        for motion, keywords in _FORBIDDEN_KEYWORDS.items()
        if any(_keyword_matches(text_lower, keyword) for keyword in keywords)
    ]
    if forbidden_match:
        return {
            "original_action": original,
            "stabilized_action": "static confrontation / reaction close-up / insert shot with restrained motion",
            "stabilization_reason": "Contains forbidden direct motion; converted into stable cinematic beats for LTX2.3.",
            "matched_rules": [],
            "forbidden_match": _dedupe_text(forbidden_match),
        }

    return {
        "original_action": original,
        "stabilized_action": f"{original}; keep movement restrained with subtle breathing, slow eye movement, slight cloth movement, or a slow push in",
        "stabilization_reason": "No high-risk direct motion detected; kept as a low-motion cinematic storyboard beat.",
        "matched_rules": [],
        "forbidden_match": [],
    }


def _translation_rules_for_policy() -> list[dict[str, str]]:
    return [
        {
            "original_action": str(rule.get("source_action") or ""),
            "stabilized_action": str(rule.get("stabilized_action") or ""),
            "reason": str(rule.get("reason") or ""),
        }
        for rule in STABILIZATION_RULES
    ]


def build_motion_policy(
    window_size: int,
    segment_role: str,
    is_padded_window: bool,
    action_stabilization: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    applied = action_stabilization or []
    return {
        "policy": "stable_dynamic_storyboard",
        "segment_role": segment_role,
        "window_size": window_size,
        "motion_strength": os.getenv("AI_DRAMA_VIDEO_MOTION_STRENGTH", "low"),
        "identity_lock": True,
        "face_lock": True,
        "costume_lock": True,
        "scene_lock": True,
        "prop_lock": True,
        "lighting_lock": True,
        "composition_lock": True,
        "is_padded_window": is_padded_window,
        "allowed_motion": ALLOWED_STABLE_MOTION,
        "forbidden_direct_motion": FORBIDDEN_DIRECT_MOTION,
        "forbidden_changes": ["new characters", "face change", "costume change", "scene change", "new props", "subtitles", "watermark", "modern objects", *FORBIDDEN_DIRECT_MOTION],
        "translation_rules": _translation_rules_for_policy(),
        "applied_stabilization": applied,
        "instruction": "Translate high-motion story actions into stable dynamic storyboard beats before sending the prompt to LTX2.3.",
    }


def _role_prompt(segment_role: str, is_padded_window: bool) -> str:
    if segment_role == "first":
        return "Start clearly and steadily from the first keyframe. Establish the scene without sudden motion."
    if segment_role == "middle":
        return "Continue naturally from the previous segment. The first keyframe is the previous segment ending anchor."
    if segment_role == "last":
        return "End cleanly on the final keyframe. Avoid abrupt motion or new action near the end."
    if is_padded_window:
        return "The final repeated keyframes are held for a calm ending. Avoid inventing extra action."
    return "Play this single segment as a stable keyframe progression."


def build_prompt_parts(
    frame_details: list[dict[str, Any]],
    timeline_text: str,
    segment_role: str,
    is_padded_window: bool,
    edit_rhythm_text: str = "",
) -> dict[str, Any]:
    base = os.getenv(
        "AI_DRAMA_VIDEO_PROMPT_TEMPLATE",
        "Use the provided storyboard keyframe image group as the exact visual anchor. Keep the same character identity, face, costume, scene, props, lighting, composition style, and historical era. Only animate stable cinematic storyboard motion: slow push in, subtle breathing, slight cloth movement, candle flicker, snow/rain/fog movement, slow eye movement, slight head turn, hand grip close-up, static confrontation, reaction close-up, or insert shot. Do not directly animate running, fighting, body-moving hugs, spinning camera, large body turns, multi-person physical interaction, complex hand action, or fast camera movement. Do not add new characters or props. Do not change face, costume, scene, layout, or era. No subtitles, no captions, no typography, no watermark.",
    )
    action_stabilization = [stabilize_action(str(frame.get("story_action") or "")) for frame in frame_details]
    action_lines = [
        "Animate a smooth progression across the provided keyframes as stable dynamic cinematic storyboard beats.",
        "Use only the stabilized actions below; do not directly animate any forbidden high-motion original action.",
        "Keyframe progression:",
    ]
    for idx, frame in enumerate(frame_details, start=1):
        stable = action_stabilization[idx - 1]
        action_lines.append(f"{idx}. {stable.get('stabilized_action')} | emotion: {frame.get('emotion')} | camera: {frame.get('camera_plan')}")
    continuity = "; ".join(str(frame.get("continuity_notes") or "").strip() for frame in frame_details if frame.get("continuity_notes"))
    if continuity:
        action_lines.append(f"Continuity: {continuity}")
    if is_padded_window:
        action_lines.append("Padded ending: repeated final keyframes should be treated as a held ending pose, not as a reason to invent new action.")
    audio_prompt = f"Audio acting beats: {timeline_text}" if timeline_text else "Audio acting beats: follow the current audio segment timing with restrained acting."
    rhythm_prompt = f"Editing rhythm guide: {edit_rhythm_text}" if edit_rhythm_text else "Editing rhythm guide: use a calm default rhythm with restrained motion."
    role_prompt = _role_prompt(segment_role, is_padded_window)
    final_prompt = "\n\n".join([base, role_prompt, "\n".join(action_lines), audio_prompt, rhythm_prompt]).strip()
    return {
        "base_video_prompt": base,
        "segment_role_prompt": role_prompt,
        "window_action_prompt": "\n".join(action_lines),
        "audio_acting_prompt": audio_prompt,
        "edit_rhythm_prompt": rhythm_prompt,
        "final_ltx_prompt": final_prompt,
        "original_action": " | ".join(f"{idx}. {item.get('original_action')}" for idx, item in enumerate(action_stabilization, start=1)),
        "stabilized_action": " | ".join(f"{idx}. {item.get('stabilized_action')}" for idx, item in enumerate(action_stabilization, start=1)),
        "stabilization_reason": " | ".join(f"{idx}. {item.get('stabilization_reason')}" for idx, item in enumerate(action_stabilization, start=1)),
        "action_stabilization": action_stabilization,
    }


def build_window_ltx_prompt(frame_details: list[dict[str, Any]], timeline_text: str, segment_role: str = "middle", is_padded_window: bool = False) -> str:
    return build_prompt_parts(frame_details, timeline_text, segment_role, is_padded_window)["final_ltx_prompt"]


build_ltx_prompt = build_window_ltx_prompt


def build_segment_plan(
    image_manifest: dict[str, Any],
    audio_timeline: dict[str, Any],
    final_audio_path: str | Path,
    output_dir: str | Path,
    storyboard: dict[str, Any] | None = None,
    edit_rhythm: dict[str, Any] | None = None,
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
    rhythm_entries = _edit_rhythm_entries(edit_rhythm)
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
        window_record = windows[(index - 1) % len(windows)]
        window = window_record["items"]
        is_padded_window = bool(window_record.get("is_padded_window"))
        padded_frame_count = int(window_record.get("padded_frame_count") or 0)
        role = _segment_role(index, segment_count)
        frame_details = [_frame_detail(image, frame_index, fallback_number=i) for i, image in enumerate(window, start=1)]
        image_paths = [str(frame.get("image_path") or "") for frame in frame_details]
        frame_ids = [str(frame.get("frame_id") or f"frame_{i:04d}") for i, frame in enumerate(frame_details, start=1)]
        clip_name = f"clip_{index:04d}.mp4"
        slice_name = f"audio_slice_{index:04d}.wav"
        timeline_text = _timeline_text(entries, start, end)
        rhythm_text = _edit_rhythm_text(rhythm_entries, start, end)
        prompt_parts = build_prompt_parts(frame_details, timeline_text, role, is_padded_window, edit_rhythm_text=rhythm_text)
        motion_policy = build_motion_policy(window_size, role, is_padded_window, prompt_parts.get("action_stabilization", []))
        segments.append(
            {
                "segment_id": f"video_seg_{index:04d}",
                "segment_index": index,
                "segment_role": role,
                "window_mode": window_mode,
                "window_size": window_size,
                "stride": stride,
                "frame_ids": frame_ids,
                "image_paths": image_paths,
                "keyframe_details": frame_details,
                "anchor_frame_id": frame_ids[-1] if frame_ids else None,
                "is_padded_window": is_padded_window,
                "padded_frame_count": padded_frame_count,
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
                "edit_rhythm_text": rhythm_text,
                "prompt_parts": prompt_parts,
                "original_action": prompt_parts.get("original_action"),
                "stabilized_action": prompt_parts.get("stabilized_action"),
                "stabilization_reason": prompt_parts.get("stabilization_reason"),
                "ltx_prompt": prompt_parts["final_ltx_prompt"],
                "negative_prompt": negative_prompt,
                "motion_policy": motion_policy,
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
            {
                "window_index": idx,
                "frame_ids": [str(img.get("frame_id")) for img in record["items"]],
                "image_paths": [str(img.get("image_path")) for img in record["items"]],
                "is_padded_window": bool(record.get("is_padded_window")),
                "padded_frame_count": int(record.get("padded_frame_count") or 0),
            }
            for idx, record in enumerate(windows, start=1)
        ],
        "segments": segments,
        "settings": {
            "fps": fps,
            "width": width,
            "height": height,
            "overlap_frames": overlap_frames,
            "edit_rhythm_enabled": bool(rhythm_entries),
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
        "segment_role": segment.get("segment_role"),
        "edit_rhythm_text": segment.get("edit_rhythm_text"),
        "output_clip_path": segment.get("output_clip_path"),
        "output_basename": segment.get("output_basename"),
        "image_paths": image_paths,
        "image_path": image_paths[0] if image_paths else None,
    }
    for idx in range(1, 10):
        payload[f"image_{idx}"] = image_paths[idx - 1] if idx <= len(image_paths) else ""
    return payload
