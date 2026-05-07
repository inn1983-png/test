from __future__ import annotations

from typing import Any


def build_retry_plan(
    character_lock_manifest: dict[str, Any],
    appearance_manifest: dict[str, Any],
    reference_asset_manifest: dict[str, Any],
    image_manifest: dict[str, Any],
) -> dict[str, Any]:
    retry_character_lock = [item.get("lock_key") for item in character_lock_manifest.get("character_locks", []) or [] if isinstance(item, dict) and item.get("status") == "failed"]
    retry_appearance = [item.get("appearance_asset_key") for item in appearance_manifest.get("appearances", []) or [] if isinstance(item, dict) and item.get("status") == "failed"]
    retry_reference_assets = []
    for item in (reference_asset_manifest.get("scene_assets", []) or []) + (reference_asset_manifest.get("prop_assets", []) or []):
        if isinstance(item, dict) and item.get("status") == "failed":
            retry_reference_assets.append(item.get("scene_key") or item.get("prop_key") or item.get("asset_key"))
    retry_frames = [item.get("frame_id") for item in image_manifest.get("images", []) or [] if isinstance(item, dict) and item.get("status") == "failed"]
    return {
        "needs_retry": bool(retry_character_lock or retry_appearance or retry_reference_assets or retry_frames),
        "retry_character_lock": retry_character_lock,
        "retry_appearance": retry_appearance,
        "retry_reference_assets": retry_reference_assets,
        "retry_frames": retry_frames,
        "retry_policy": "local image phase retry only; do not rerun 06 unless dependency binding is broken",
    }
