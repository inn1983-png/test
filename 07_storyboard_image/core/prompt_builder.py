from __future__ import annotations

import os
from typing import Any


def style_suffix() -> str:
    return os.getenv(
        "AI_DRAMA_IMAGE_STYLE_SUFFIX",
        "Chinese historical drama, cinematic realistic live-action style, natural color, ancient China setting, consistent characters, stable scene, high detail, no modern objects",
    )


def negative_prompt() -> str:
    return os.getenv(
        "AI_DRAMA_IMAGE_NEGATIVE_PROMPT",
        "modern objects, modern clothing, western face, cartoon, anime, 3d render, low quality, blurry, extra limbs, deformed hands, wrong gender, duplicate people, text, watermark",
    )


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def character_lock_prompt(task: dict[str, Any], character_card: dict[str, Any] | None = None) -> str:
    card = character_card or {}
    return "\n".join([
        f"角色定妆图：{task.get('canonical_name', '')}",
        "单人正面或标准三分之四角度，背景干净，脸部清晰，身份稳定。",
        f"角色外观：{_to_text(card.get('appearance', ''))}",
        f"默认服装：{_to_text(card.get('costume', ''))}",
        f"参考计划：{_to_text(card.get('reference_image_plan', ''))}",
        style_suffix(),
    ])


def appearance_prompt(task: dict[str, Any], character_card: dict[str, Any] | None = None) -> str:
    card = character_card or {}
    wearable = ", ".join(map(str, task.get("wearable_props", []) or []))
    return "\n".join([
        f"角色造型图：{task.get('canonical_name', '')}",
        f"保持定妆图同一张脸：{task.get('base_lock_key', '')}",
        f"服装版本 costume_id：{task.get('costume_id', '')}",
        f"常驻穿戴物：{wearable if wearable else '无'}",
        "单人造型图，人物清晰，服装完整，方便后续分镜作为角色参考图。",
        f"角色基础外观：{_to_text(card.get('appearance', ''))}",
        style_suffix(),
    ])


def reference_asset_prompt(task: dict[str, Any]) -> str:
    if task.get("asset_kind") == "scene":
        return "\n".join([
            f"场景参考图：{task.get('scene_key') or task.get('asset_key', '')}",
            "空镜或低人物干扰，空间结构清晰，光源稳定，方便后续分镜复用。",
            style_suffix(),
        ])
    return "\n".join([
        f"道具参考图：{task.get('prop_key') or task.get('asset_key', '')}",
        "单一道具，真实材质，背景干净，方便后续分镜引用。",
        style_suffix(),
    ])


def storyboard_frame_prompt(task: dict[str, Any], source_frame: dict[str, Any] | None = None) -> str:
    frame = source_frame or task.get("source_frame") or {}
    chars = []
    for char in frame.get("characters", []) or []:
        if isinstance(char, dict):
            chars.append(f"{char.get('canonical_name', '')}/{char.get('appearance_asset_key', '')}/{char.get('costume_id', '')}")
    props = []
    for prop in frame.get("props", []) or []:
        if isinstance(prop, dict):
            props.append(str(prop.get("canonical_prop_name", "")))
        elif prop:
            props.append(str(prop))
    scene = frame.get("scene", {})
    scene_name = scene.get("canonical_scene_name", "") if isinstance(scene, dict) else str(scene or "")
    return "\n".join([
        f"正式单帧分镜：{task.get('frame_id', '')}",
        f"场景：{scene_name}",
        f"角色：{' | '.join([c for c in chars if c]) if chars else '无主要人物'}",
        f"道具：{', '.join([p for p in props if p]) if props else '无关键道具'}",
        f"剧情动作：{frame.get('story_action', '')}",
        f"情绪：{frame.get('emotion', '')}",
        f"镜头：{_to_text(frame.get('camera_plan', ''))}",
        f"构图：{frame.get('composition_notes', '')}",
        f"连续性：{frame.get('continuity_notes', '')}",
        f"锚点帧：{task.get('anchor_frame_id') or '本帧为锚点或无'}",
        f"上一帧连续性参考：{task.get('continuity_source_frame_id') or '无'}",
        style_suffix(),
    ])
