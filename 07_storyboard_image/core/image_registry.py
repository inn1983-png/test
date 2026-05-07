from __future__ import annotations

from typing import Any


def build_registry(
    character_lock_manifest: dict[str, Any],
    appearance_manifest: dict[str, Any],
    reference_asset_manifest: dict[str, Any],
    image_manifest: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for item in character_lock_manifest.get("character_locks", []) or []:
        if isinstance(item, dict):
            entries.append({
                "registry_key": item.get("lock_key"),
                "category": "character_lock",
                "business_key": item.get("canonical_name"),
                "image_path": item.get("selected_image_path"),
                "status": item.get("status"),
                "revision": item.get("revision", 1),
            })
    for item in appearance_manifest.get("appearances", []) or []:
        if isinstance(item, dict):
            entries.append({
                "registry_key": item.get("appearance_asset_key"),
                "category": "character_appearance",
                "business_key": item.get("canonical_name"),
                "image_path": item.get("selected_image_path"),
                "status": item.get("status"),
                "revision": item.get("revision", 1),
            })
    for item in reference_asset_manifest.get("scene_assets", []) or []:
        if isinstance(item, dict):
            entries.append({
                "registry_key": item.get("scene_key"),
                "category": "scene_reference",
                "business_key": item.get("scene_key"),
                "image_path": item.get("selected_image_path"),
                "status": item.get("status"),
                "revision": item.get("revision", 1),
            })
    for item in reference_asset_manifest.get("prop_assets", []) or []:
        if isinstance(item, dict):
            entries.append({
                "registry_key": item.get("prop_key"),
                "category": "prop_reference",
                "business_key": item.get("prop_key"),
                "image_path": item.get("selected_image_path"),
                "status": item.get("status"),
                "revision": item.get("revision", 1),
            })
    for item in image_manifest.get("images", []) or []:
        if isinstance(item, dict):
            entries.append({
                "registry_key": item.get("frame_id"),
                "category": "storyboard_frame",
                "business_key": item.get("frame_id"),
                "image_path": item.get("image_path"),
                "status": item.get("status"),
                "revision": item.get("revision", 1),
            })
    return {"schema_version": "1.1", "entries": entries}
