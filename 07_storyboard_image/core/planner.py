from __future__ import annotations

from typing import Any
from importlib import import_module

path_resolver = import_module("07_storyboard_image.core.path_resolver")
dependency_graph = import_module("07_storyboard_image.core.dependency_graph")


def _scene_name(frame: dict[str, Any]) -> str:
    scene = frame.get("scene")
    if isinstance(scene, dict):
        return str(scene.get("canonical_scene_name", ""))
    return str(scene or "")


def _prop_name(prop: Any) -> str:
    if isinstance(prop, dict):
        return str(prop.get("canonical_prop_name", ""))
    return str(prop or "")


def _character_level_map(characters: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in characters.get("characters", []) or []:
        if isinstance(item, dict) and item.get("canonical_name"):
            result[str(item["canonical_name"])] = str(item.get("asset_level", ""))
    return result


def _needs_fixed_face_map(characters: dict[str, Any]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for item in characters.get("characters", []) or []:
        if isinstance(item, dict) and item.get("canonical_name"):
            result[str(item["canonical_name"])] = bool(item.get("needs_fixed_face", False))
    return result


def build_plan(storyboard: dict[str, Any], characters: dict[str, Any], scenes: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    frames = [frame for frame in storyboard.get("frames", []) or [] if isinstance(frame, dict)]
    level_map = _character_level_map(characters)
    fixed_face_map = _needs_fixed_face_map(characters)

    used_characters: dict[str, dict[str, Any]] = {}
    for frame in frames:
        for char in frame.get("characters", []) or []:
            if not isinstance(char, dict):
                continue
            name = str(char.get("canonical_name", "")).strip()
            if not name:
                continue
            row = used_characters.setdefault(name, {"canonical_name": name, "frame_ids": [], "appearance_asset_keys": set()})
            row["frame_ids"].append(frame.get("frame_id"))
            if char.get("appearance_asset_key"):
                row["appearance_asset_keys"].add(str(char["appearance_asset_key"]))

    character_lock_tasks: list[dict[str, Any]] = []
    for name, row in sorted(used_characters.items(), key=lambda item: item[0]):
        asset_level = level_map.get(name, "")
        needs_fixed_face = fixed_face_map.get(name, False)
        should_generate = needs_fixed_face or asset_level in {"main", "supporting", "main_character", "supporting_character"} or len(row["frame_ids"]) >= 2
        if not should_generate:
            continue
        lock_key = f"charlock_{path_resolver.safe_key(name)}"
        character_lock_tasks.append({
            "task_id": f"07A_{lock_key}",
            "lock_key": lock_key,
            "canonical_name": name,
            "asset_level": asset_level,
            "needs_fixed_face": needs_fixed_face,
            "source_frame_ids": row["frame_ids"],
            "downstream_appearance_keys": sorted(row["appearance_asset_keys"]),
            "output_image_path": "",
            "status": "pending",
        })

    lock_by_name = {task["canonical_name"]: task["lock_key"] for task in character_lock_tasks}
    appearance_tasks: list[dict[str, Any]] = []
    seen_app: set[str] = set()
    for req in storyboard.get("appearance_asset_requirements", []) or []:
        if not isinstance(req, dict):
            continue
        app_key = str(req.get("appearance_asset_key", "")).strip()
        name = str(req.get("canonical_name", "")).strip()
        if not app_key or app_key in seen_app:
            continue
        seen_app.add(app_key)
        appearance_tasks.append({
            "task_id": f"07B_app_{path_resolver.safe_key(app_key)}",
            "appearance_asset_key": app_key,
            "canonical_name": name,
            "costume_id": req.get("costume_id", ""),
            "wearable_props": req.get("wearable_props", []) if isinstance(req.get("wearable_props", []), list) else [],
            "base_lock_key": lock_by_name.get(name, f"charlock_{path_resolver.safe_key(name)}"),
            "source_frame_ids": req.get("source_frame_ids", []) if isinstance(req.get("source_frame_ids", []), list) else [],
            "output_image_path": "",
            "status": "pending",
        })

    scene_tasks: dict[str, dict[str, Any]] = {}
    prop_tasks: dict[str, dict[str, Any]] = {}
    storyboard_frame_tasks: list[dict[str, Any]] = []
    current_anchor: str | None = None
    last_scene = ""
    previous_frame_id: str | None = None
    for frame in frames:
        frame_id = str(frame.get("frame_id", ""))
        seq = frame.get("sequence_index", 0)
        scene_name = _scene_name(frame)
        if scene_name:
            scene_tasks.setdefault(scene_name, {
                "task_id": f"07C_scene_{path_resolver.safe_key(scene_name)}",
                "scene_key": scene_name,
                "asset_kind": "scene",
                "source_frame_ids": [],
                "output_image_path": "",
                "status": "pending",
            })
            scene_tasks[scene_name]["source_frame_ids"].append(frame_id)
        prop_keys: list[str] = []
        for prop in frame.get("props", []) or []:
            prop_name = _prop_name(prop)
            if not prop_name:
                continue
            prop_keys.append(prop_name)
            prop_tasks.setdefault(prop_name, {
                "task_id": f"07C_prop_{path_resolver.safe_key(prop_name)}",
                "prop_key": prop_name,
                "asset_kind": "prop",
                "source_frame_ids": [],
                "output_image_path": "",
                "status": "pending",
            })
            prop_tasks[prop_name]["source_frame_ids"].append(frame_id)
        appearance_keys = []
        for char in frame.get("characters", []) or []:
            if isinstance(char, dict) and char.get("appearance_asset_key"):
                appearance_keys.append(str(char["appearance_asset_key"]))
        is_anchor = scene_name != last_scene or not current_anchor or any(str(char.get("appearance_asset_key", "")) not in seen_app for char in frame.get("characters", []) or [] if isinstance(char, dict))
        if is_anchor:
            current_anchor = frame_id
        storyboard_frame_tasks.append({
            "task_id": f"07D_frame_{path_resolver.safe_key(frame_id)}",
            "frame_id": frame_id,
            "sequence_index": seq,
            "scene_ref_key": scene_name,
            "appearance_asset_keys": appearance_keys,
            "prop_ref_keys": prop_keys,
            "is_anchor_frame": bool(is_anchor),
            "anchor_frame_id": None if is_anchor else current_anchor,
            "continuity_source_frame_id": previous_frame_id if not is_anchor else None,
            "output_image_path": "",
            "status": "pending",
        })
        previous_frame_id = frame_id
        last_scene = scene_name

    plan = {
        "schema_version": "1.1",
        "stage": "07P_plan",
        "status": "planned",
        "character_lock_tasks": character_lock_tasks,
        "appearance_tasks": appearance_tasks,
        "reference_asset_tasks": list(scene_tasks.values()) + list(prop_tasks.values()),
        "scene_reference_tasks": list(scene_tasks.values()),
        "prop_reference_tasks": list(prop_tasks.values()),
        "storyboard_frame_tasks": storyboard_frame_tasks,
        "planning_policy": {
            "character_lock": "generate only fixed-face or repeatedly used main/supporting characters",
            "appearance": "generate only appearance_asset_requirements actually used by 06",
            "reference_assets": "generate/register only scenes and props used by this storyboard",
            "storyboard_frame": "anchor frames first, then normal frames can use anchor/previous frame continuity",
        },
    }
    plan["dependency_index"] = dependency_graph.build_dependency_index(plan)
    return plan
