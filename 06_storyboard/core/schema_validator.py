from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "appearance_asset_requirements", "frames", "allowed_asset_names",
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


def _asset_names(assets: dict[str, Any]) -> tuple[set[str], set[str], set[str], dict[str, set[str]]]:
    characters = set()
    character_costumes: dict[str, set[str]] = {}
    for item in assets.get("characters", []) or []:
        if isinstance(item, dict) and item.get("canonical_name"):
            name = str(item["canonical_name"])
            characters.add(name)
            costume_ids: set[str] = set()
            for costume in item.get("costume_variants", []) or []:
                if isinstance(costume, dict) and costume.get("costume_id"):
                    costume_ids.add(str(costume["costume_id"]))
            character_costumes[name] = costume_ids
    scenes = set()
    for item in assets.get("scenes", []) or []:
        if isinstance(item, dict) and item.get("canonical_scene_name"):
            scenes.add(str(item["canonical_scene_name"]))
    props = set()
    for item in assets.get("props", []) or []:
        if isinstance(item, dict) and item.get("canonical_prop_name"):
            props.add(str(item["canonical_prop_name"]))
    return characters, scenes, props, character_costumes


def _allowed_costumes(allowed: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for item in allowed.get("character_costumes", []) or []:
        if isinstance(item, dict) and item.get("canonical_name"):
            result[str(item["canonical_name"])] = set(map(str, item.get("costume_ids", []) or []))
    return result


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

    appearance_reqs = data.get("appearance_asset_requirements", [])
    if not isinstance(appearance_reqs, list) or not appearance_reqs:
        issues.append("appearance_asset_requirements 为空或不是数组")
        appearance_reqs = []
    appearance_keys: set[str] = set()
    for idx, req in enumerate(appearance_reqs):
        if not isinstance(req, dict):
            issues.append(f"appearance_asset_requirements[{idx}] 不是对象")
            continue
        for field in ["appearance_asset_key", "canonical_name", "character_lock_reference", "costume_id", "wearable_props", "source_frame_ids", "usage_note"]:
            if field not in req:
                issues.append(f"appearance_asset_requirements[{idx}] 缺少字段：{field}")
        key = str(req.get("appearance_asset_key", "")).strip()
        if key in appearance_keys:
            issues.append(f"appearance_asset_key 重复：{key}")
        if key:
            appearance_keys.add(key)
        if not isinstance(req.get("wearable_props", []), list):
            issues.append(f"appearance_asset_requirements[{idx}].wearable_props 必须为数组")

    allowed = data.get("allowed_asset_names", {}) if isinstance(data.get("allowed_asset_names"), dict) else {}
    allowed_characters = set(map(str, allowed.get("characters", []) or []))
    allowed_scenes = set(map(str, allowed.get("scenes", []) or []))
    allowed_props = set(map(str, allowed.get("props", []) or []))
    allowed_character_costumes = _allowed_costumes(allowed)
    if assets:
        asset_characters, asset_scenes, asset_props, asset_character_costumes = _asset_names(assets)
        if allowed_characters - asset_characters:
            issues.append(f"allowed_asset_names.characters 含资产库不存在角色：{sorted(allowed_characters - asset_characters)}")
        if allowed_scenes - asset_scenes:
            issues.append(f"allowed_asset_names.scenes 含资产库不存在场景：{sorted(allowed_scenes - asset_scenes)}")
        if allowed_props - asset_props:
            issues.append(f"allowed_asset_names.props 含资产库不存在道具：{sorted(allowed_props - asset_props)}")
        for name, costume_ids in allowed_character_costumes.items():
            real_ids = asset_character_costumes.get(name, set())
            if costume_ids - real_ids:
                issues.append(f"allowed_asset_names.character_costumes 含不存在 costume_id：{name} -> {sorted(costume_ids - real_ids)}")

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
            if not isinstance(char, dict):
                issues.append(f"分镜 {fid or idx} characters 必须为对象数组")
                continue
            name = str(char.get("canonical_name", ""))
            costume_id = str(char.get("costume_id", ""))
            appearance_key = str(char.get("appearance_asset_key", ""))
            if name and allowed_characters and name not in allowed_characters:
                issues.append(f"分镜 {fid or idx} 引用了不存在/不允许的角色：{name}")
            if not name:
                issues.append(f"分镜 {fid or idx} 存在空角色名")
            if not costume_id:
                issues.append(f"分镜 {fid or idx} 角色缺少 costume_id：{name}")
            elif allowed_character_costumes and costume_id not in allowed_character_costumes.get(name, set()):
                issues.append(f"分镜 {fid or idx} 角色引用了不存在/不允许的 costume_id：{name}/{costume_id}")
            if not appearance_key:
                issues.append(f"分镜 {fid or idx} 角色缺少 appearance_asset_key：{name}")
            elif appearance_keys and appearance_key not in appearance_keys:
                issues.append(f"分镜 {fid or idx} appearance_asset_key 未在 appearance_asset_requirements 中定义：{appearance_key}")
            if "character_lock_reference" not in char:
                issues.append(f"分镜 {fid or idx} 角色缺少 character_lock_reference：{name}")
            if not isinstance(char.get("wearable_props", []), list):
                issues.append(f"分镜 {fid or idx} 角色 wearable_props 必须为数组：{name}")
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
