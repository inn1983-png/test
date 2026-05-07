from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
SUCCESS_STATUSES = {"success", "planned", "skipped"}
VALID_SCOPES = {"all", "failed", "frame", "character_lock", "appearance", "reference_asset"}


def normalize_retry_options(options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    scope = str(options.get("retry_scope") or "all").strip().lower()
    if scope not in VALID_SCOPES:
        raise ValueError(f"unsupported retry_scope: {scope}")
    return {
        "retry_scope": scope,
        "frame_id": str(options.get("frame_id") or "").strip(),
        "asset_key": str(options.get("asset_key") or "").strip(),
        "force": bool(options.get("force", False)),
    }


def _path_exists(path_value: Any) -> bool:
    if not isinstance(path_value, str) or not path_value:
        return False
    path = Path(path_value)
    if path.exists():
        return True
    return (ROOT_DIR / path_value).exists()


def existing_keyed(rows: list[dict[str, Any]] | None, key_names: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for key in key_names:
            value = row.get(key)
            if value:
                result[str(value)] = row
                break
    return result


def should_run_item(category: str, item_key: str, existing: dict[str, Any] | None, options: dict[str, Any] | None = None) -> bool:
    opts = normalize_retry_options(options)
    scope = opts["retry_scope"]
    status = str((existing or {}).get("status") or "").lower()
    if scope == "all":
        return True
    if scope == "failed":
        return status == "failed"
    if scope == "frame":
        return category == "frame" and item_key == opts["frame_id"]
    if scope == "character_lock":
        return category == "character_lock" and item_key == opts["asset_key"]
    if scope == "appearance":
        return category == "appearance" and item_key == opts["asset_key"]
    if scope == "reference_asset":
        return category == "reference_asset" and item_key == opts["asset_key"]
    return False


def should_skip_success(existing: dict[str, Any] | None, output_path: Any, options: dict[str, Any] | None = None) -> bool:
    opts = normalize_retry_options(options)
    if opts["force"] or not existing:
        return False
    status = str(existing.get("status") or "").lower()
    existing_path = existing.get("image_path") or existing.get("selected_image_path") or output_path
    return status in SUCCESS_STATUSES and _path_exists(existing_path)


def mark_skipped_existing(existing: dict[str, Any], reason: str = "existing_success_not_overwritten") -> dict[str, Any]:
    row = dict(existing)
    row["skipped_this_run"] = True
    row["skip_reason"] = reason
    return row


def retry_count(existing: dict[str, Any] | None) -> int:
    try:
        return int((existing or {}).get("retry_count") or 0)
    except (TypeError, ValueError):
        return 0


def append_retry_history(manifest: dict[str, Any], options: dict[str, Any] | None, generated: list[str], skipped: list[str]) -> dict[str, Any]:
    opts = normalize_retry_options(options)
    history = manifest.get("retry_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "retry_scope": opts["retry_scope"],
            "frame_id": opts["frame_id"],
            "asset_key": opts["asset_key"],
            "force": opts["force"],
            "generated": generated,
            "skipped_existing_success": skipped,
        }
    )
    manifest["retry_history"] = history
    return manifest

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
