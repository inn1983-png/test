from __future__ import annotations

"""Runtime style hook for scripts launched from 00_main_controller.

Python automatically imports sitecustomize from the script directory during
startup. run_pipeline.py is launched from 00_main_controller, so this hook is a
low-risk way to patch long downstream modules without overwriting them.

Purpose:
- UI passes only one selected style preset id.
- 00_style_system generates one STYLE_BIBLE from that id.
- 09_video must use video_style_lock.txt and style_negative_prompt.txt when it
  builds LTX prompts.
"""

import os
import sys
import importlib
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_ORIGINAL_IMPORT_MODULE = importlib.import_module
_PATCHED_MODULES: set[str] = set()

DEFAULT_VIDEO_BASE_PROMPT = (
    "Use the provided storyboard keyframe image group as the exact visual anchor. "
    "Keep the same character identity, face, costume, scene, props, lighting, composition style, and historical era. "
    "Only animate stable cinematic storyboard motion: slow push in, subtle breathing, slight cloth movement, candle flicker, "
    "snow/rain/fog movement, slow eye movement, slight head turn, hand grip close-up, static confrontation, reaction close-up, or insert shot. "
    "Do not directly animate running, fighting, body-moving hugs, spinning camera, large body turns, multi-person physical interaction, complex hand action, or fast camera movement. "
    "Do not add new characters or props. Do not change face, costume, scene, layout, or era. No subtitles, no captions, no typography, no watermark."
)

DEFAULT_VIDEO_NEGATIVE = (
    "subtitles, captions, text, typography, watermark, logo, extra characters, new person, face change, identity change, "
    "costume change, scene change, prop change, modern objects, modern clothes, wrong era, cartoon, anime, 3d render, "
    "low quality, blurry, distorted face, bad hands, extra limbs, deformed body, flicker, camera shake"
)


def _run_dir() -> str:
    return os.getenv("AI_DRAMA_RUN_DIR", "").strip()


def _style_context():
    try:
        return _ORIGINAL_IMPORT_MODULE("00_common.style_context")
    except Exception:
        return None


def _video_style_lock() -> str:
    ctx = _style_context()
    if not ctx or not _run_dir():
        return ""
    try:
        return str(ctx.load_video_style_lock(_run_dir()) or "").strip()
    except Exception:
        return ""


def _style_negative_prompt() -> str:
    ctx = _style_context()
    if not ctx or not _run_dir():
        return ""
    try:
        return str(ctx.load_style_negative_prompt(_run_dir()) or "").strip()
    except Exception:
        return ""


def _dedupe_csv(parts: list[str]) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for part in ", ".join(p for p in parts if p).split(","):
        text = part.strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return ", ".join(output)


def _patch_workflow_adapter(module: Any) -> Any:
    if getattr(module, "__style_bible_patched__", False):
        return module

    original_stabilize_action = getattr(module, "stabilize_action", None)
    original_role_prompt = getattr(module, "_role_prompt", None)

    def build_negative_prompt() -> str:
        locked = _style_negative_prompt()
        manual = os.getenv("AI_DRAMA_VIDEO_NEGATIVE_PROMPT", "").strip()
        return _dedupe_csv([locked, manual or DEFAULT_VIDEO_NEGATIVE])

    def build_prompt_parts(
        frame_details: list[dict[str, Any]],
        timeline_text: str,
        segment_role: str,
        is_padded_window: bool,
        edit_rhythm_text: str = "",
    ) -> dict[str, Any]:
        manual_template = os.getenv("AI_DRAMA_VIDEO_PROMPT_TEMPLATE", "").strip()
        style_lock = _video_style_lock()
        base_template = manual_template or DEFAULT_VIDEO_BASE_PROMPT
        base = "\n\n".join(part for part in [style_lock, base_template] if part).strip()

        stabilize = original_stabilize_action or (lambda action: {
            "original_action": str(action or ""),
            "stabilized_action": str(action or "hold the visual state shown in this keyframe"),
            "stabilization_reason": "fallback stabilization",
            "matched_rules": [],
            "forbidden_match": [],
        })
        role_builder = original_role_prompt or (lambda role, padded: "Play this segment as a stable keyframe progression.")

        action_stabilization = [stabilize(str(frame.get("story_action") or "")) for frame in frame_details]
        action_lines = [
            "Animate a smooth progression across the provided keyframes as stable dynamic cinematic storyboard beats.",
            "Use only the stabilized actions below; do not directly animate any forbidden high-motion original action.",
            "Keyframe progression:",
        ]
        for idx, frame in enumerate(frame_details, start=1):
            stable = action_stabilization[idx - 1]
            action_lines.append(
                f"{idx}. {stable.get('stabilized_action')} | emotion: {frame.get('emotion')} | camera: {frame.get('camera_plan')}"
            )
        continuity = "; ".join(str(frame.get("continuity_notes") or "").strip() for frame in frame_details if frame.get("continuity_notes"))
        if continuity:
            action_lines.append(f"Continuity: {continuity}")
        if is_padded_window:
            action_lines.append("Padded ending: repeated final keyframes should be treated as a held ending pose, not as a reason to invent new action.")

        audio_prompt = f"Audio acting beats: {timeline_text}" if timeline_text else "Audio acting beats: follow the current audio segment timing with restrained acting."
        rhythm_prompt = f"Editing rhythm guide: {edit_rhythm_text}" if edit_rhythm_text else "Editing rhythm guide: use a calm default rhythm with restrained motion."
        role_prompt = role_builder(segment_role, is_padded_window)
        final_prompt = "\n\n".join([base, role_prompt, "\n".join(action_lines), audio_prompt, rhythm_prompt]).strip()
        return {
            "video_style_lock": style_lock,
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

    module.build_negative_prompt = build_negative_prompt
    module.build_prompt_parts = build_prompt_parts
    module.build_window_ltx_prompt = build_window_ltx_prompt
    module.build_ltx_prompt = build_window_ltx_prompt
    module.__style_bible_patched__ = True
    return module


def _wrapped_import_module(name: str, package: str | None = None):
    module = _ORIGINAL_IMPORT_MODULE(name, package)
    if name == "09_video.core.workflow_adapter" and name not in _PATCHED_MODULES:
        _patch_workflow_adapter(module)
        _PATCHED_MODULES.add(name)
    return module


importlib.import_module = _wrapped_import_module
