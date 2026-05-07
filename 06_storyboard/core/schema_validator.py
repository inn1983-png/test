from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "frames", "allowed_asset_names",
    "asset_availability_report", "storyboard_plan", "frame_group_plan", "continuity_map",
    "four_grid_preview_groups", "upstream_blocking_issues", "quality_report"
]
REQUIRED_FRAME_FIELDS = [
    "frame_id", "sequence_index", "source_segment_ids", "source_voice_line_ids", "source_visual_unit_ids",
    "scene", "characters", "props", "story_action", "emotion", "camera_plan",
    "reference_requirements", "composition_notes", "continuity_notes", "next_frame_link"
]
FORBIDDEN_FIELDS = {"prompt", "image_prompt", "desc_prompt", "desc_promopt", "negative_prompt", "video_prompt", "comfyui_prompt"}


def _contains_forbidden(value: Any, path: str = "$") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in FORBIDDEN_FIELDS:
                issues.append(f"禁止字段：{child_path}")
            issues.extend(_contains_forbidden(child, child_path))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            issues.extend(_contains_forbidden(item, f"{path}[{idx}]"))
    return issues


def _asset_names(assets: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    characters = set()
    for item in assets.get("characters", []) or []:
        if isinstance(item, dict) and item.get("canonical_name"):
            characters.add(str(item["canonical_name"]))
    scenes = set()
    for item in assets.get("scenes", []) or []:
        if isinstance(item, dict) and item.get("canonical_scene_name"):
            scenes.add(str(item["canonical_scene_name"]))
    props = set()
    for item in assets.get("props", []) or []:
        if isinstance(item, dict) and item.get("canonical_prop_name"):
            props.add(str(item["canonical_prop_name"]))
    return characters, scenes, props


def validate_final_output(data: dict[str, Any], assets: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    issues.extend(_contains_forbidden(data))

    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        issues.append("frames 为空或不是数组")
        frames = []

    allowed = data.get("allowed_asset_names", {}) if isinstance(data.get("allowed_asset_names"), dict) else {}
    allowed_characters = set(map(str, allowed.get("characters", []) or []))
    allowed_scenes = set(map(str, allowed.get("scenes", []) or []))
    allowed_props = set(map(str, allowed.get("props", []) or []))
    if assets:
        asset_characters, asset_scenes, asset_props = _asset_names(assets)
        if allowed_characters - asset_characters:
            issues.append(f"allowed_asset_names.characters 含资产库不存在角色：{sorted(allowed_characters - asset_characters)}")
        if allowed_scenes - asset_scenes:
            issues.append(f"allowed_asset_names.scenes 含资产库不存在场景：{sorted(allowed_scenes - asset_scenes)}")
        if allowed_props - asset_props:
            issues.append(f"allowed_asset_names.props 含资产库不存在道具：{sorted(allowed_props - asset_props)}")

    frame_ids: set[str] = set()
    sequence_values: set[int] = set()
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            issues.append(f"frames[{idx}] 不是对象")
            continue
        for field in REQUIRED_FRAME_FIELDS:
            if field not in frame:
                issues.append(f"分镜 {frame.get('frame_id', idx)} 缺少必要字段：{field}")
        fid = str(frame.get("frame_id", "")).strip()
        if fid in frame_ids:
            issues.append(f"frame_id 重复：{fid}")
        if fid:
            frame_ids.add(fid)
        seq = frame.get("sequence_index")
        if not isinstance(seq, int) or seq < 1:
            issues.append(f"sequence_index 必须为正整数：{fid or idx}")
        elif seq in sequence_values:
            issues.append(f"sequence_index 重复：{seq}")
        elif isinstance(seq, int):
            sequence_values.add(seq)
        scene = frame.get("scene")
        if isinstance(scene, dict):
            scene_name = str(scene.get("canonical_scene_name", ""))
        else:
            scene_name = str(scene or "")
        if scene_name and allowed_scenes and scene_name not in allowed_scenes:
            issues.append(f"分镜 {fid or idx} 引用了不存在/不允许的场景：{scene_name}")
        if not scene_name:
            issues.append(f"分镜 {fid or idx} 缺少 canonical_scene_name")
        for char in frame.get("characters", []) or []:
            name = str(char.get("canonical_name", "") if isinstance(char, dict) else char)
            if name and allowed_characters and name not in allowed_characters:
                issues.append(f"分镜 {fid or idx} 引用了不存在/不允许的角色：{name}")
            if not name:
                issues.append(f"分镜 {fid or idx} 存在空角色名")
        for prop in frame.get("props", []) or []:
            name = str(prop.get("canonical_prop_name", "") if isinstance(prop, dict) else prop)
            if name and allowed_props and name not in allowed_props:
                issues.append(f"分镜 {fid or idx} 引用了不存在/不允许的道具：{name}")
            if not name:
                issues.append(f"分镜 {fid or idx} 存在空道具名")
    if sequence_values and sequence_values != set(range(1, len(sequence_values) + 1)):
        issues.append("sequence_index 必须从 1 连续递增，不允许跳号")

    readiness = data.get("asset_availability_report", {})
    if isinstance(readiness, dict) and readiness.get("ready") is False and not data.get("upstream_blocking_issues"):
        issues.append("资产不可用时必须输出 upstream_blocking_issues")
    return {"passed": not issues, "issues": issues}
