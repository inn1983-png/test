from __future__ import annotations

from typing import Any


def build_dependency_index(plan: dict[str, Any]) -> dict[str, Any]:
    lock_to_appearances: dict[str, list[str]] = {}
    appearance_to_frames: dict[str, list[str]] = {}
    scene_to_frames: dict[str, list[str]] = {}
    prop_to_frames: dict[str, list[str]] = {}
    frame_dependencies: dict[str, dict[str, Any]] = {}

    for task in plan.get("appearance_tasks", []) or []:
        if not isinstance(task, dict):
            continue
        lock_key = str(task.get("base_lock_key", ""))
        app_key = str(task.get("appearance_asset_key", ""))
        if lock_key and app_key:
            lock_to_appearances.setdefault(lock_key, []).append(app_key)

    for frame_task in plan.get("storyboard_frame_tasks", []) or []:
        if not isinstance(frame_task, dict):
            continue
        frame_id = str(frame_task.get("frame_id", ""))
        if not frame_id:
            continue
        apps = list(map(str, frame_task.get("appearance_asset_keys", []) or []))
        props = list(map(str, frame_task.get("prop_ref_keys", []) or []))
        scene_key = str(frame_task.get("scene_ref_key", ""))
        frame_dependencies[frame_id] = {
            "appearance_asset_keys": apps,
            "scene_ref_key": scene_key,
            "prop_ref_keys": props,
            "anchor_frame_id": frame_task.get("anchor_frame_id"),
            "continuity_source_frame_id": frame_task.get("continuity_source_frame_id"),
        }
        for app_key in apps:
            appearance_to_frames.setdefault(app_key, []).append(frame_id)
        if scene_key:
            scene_to_frames.setdefault(scene_key, []).append(frame_id)
        for prop_key in props:
            prop_to_frames.setdefault(prop_key, []).append(frame_id)

    invalidation_rules = {
        "character_lock_changed": "mark linked appearance tasks stale, then mark linked storyboard frames stale",
        "character_appearance_changed": "mark linked storyboard frames stale",
        "scene_reference_changed": "mark linked storyboard frames stale",
        "prop_reference_changed": "mark linked storyboard frames stale",
        "storyboard_frame_changed": "only mark that frame stale unless it is an anchor frame",
    }
    return {
        "lock_to_appearances": lock_to_appearances,
        "appearance_to_frames": appearance_to_frames,
        "scene_to_frames": scene_to_frames,
        "prop_to_frames": prop_to_frames,
        "frame_dependencies": frame_dependencies,
        "invalidation_rules": invalidation_rules,
    }
