from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")
prompt_builder = import_module("07_storyboard_image.core.prompt_builder")
path_resolver = import_module("07_storyboard_image.core.path_resolver")
workflow_router = import_module("07_storyboard_image.core.workflow_router")
retry_manager = import_module("07_storyboard_image.core.retry_manager")


def _character_map(characters: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("canonical_name")): item for item in characters.get("characters", []) or [] if isinstance(item, dict) and item.get("canonical_name")}


def _lock_map(lock_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("lock_key")): item for item in lock_manifest.get("character_locks", []) or [] if isinstance(item, dict) and item.get("lock_key")}


def run(plan: dict[str, Any], characters: dict[str, Any], lock_manifest: dict[str, Any], output_dir: str | Path, retry_options: dict[str, Any] | None = None, existing_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    cards = _character_map(characters)
    locks = _lock_map(lock_manifest)
    existing_rows = (existing_manifest or {}).get("appearances", [])
    existing_by_key = retry_manager.existing_keyed(existing_rows if isinstance(existing_rows, list) else [], ["appearance_asset_key"])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    generated: list[str] = []
    skipped: list[str] = []
    for raw in plan.get("appearance_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        appearance_key = str(task.get("appearance_asset_key") or task.get("task_id") or "")
        existing = existing_by_key.get(appearance_key)
        if not retry_manager.should_run_item("appearance", appearance_key, existing, retry_options):
            if existing:
                rows.append(existing)
            continue
        task["task_type"] = "character_appearance"
        task["workflow_config"] = workflow_router.route("character_appearance")
        base_lock = locks.get(str(task.get("base_lock_key")), {})
        task["base_lock_image_path"] = base_lock.get("selected_image_path", "")
        task["positive_prompt"] = prompt_builder.appearance_prompt(task, cards.get(str(task.get("canonical_name"))))
        task["negative_prompt"] = prompt_builder.negative_prompt()
        task["output_basename"] = path_resolver.safe_key(str(task.get("appearance_asset_key") or task.get("task_id")))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, "character_appearance", task["output_basename"])
        if retry_manager.should_skip_success(existing, task["output_image_path"], retry_options):
            rows.append(retry_manager.mark_skipped_existing(existing))
            skipped.append(appearance_key)
            continue
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
        else:
            generated.append(appearance_key)
        rows.append({
            "appearance_asset_key": task.get("appearance_asset_key"),
            "canonical_name": task.get("canonical_name"),
            "costume_id": task.get("costume_id"),
            "wearable_props": task.get("wearable_props", []),
            "base_lock_key": task.get("base_lock_key"),
            "base_lock_image_path": task.get("base_lock_image_path", ""),
            "selected_image_path": result.get("output_path"),
            "candidate_images": [result.get("output_path")] if result.get("output_path") else [],
            "source_frame_ids": task.get("source_frame_ids", []),
            "status": status,
            "revision": 1,
            "execution_result": result,
            "prompt_summary": {"positive_prompt_chars": len(task.get("positive_prompt", "")), "negative_prompt_chars": len(task.get("negative_prompt", ""))},
            "retry_count": retry_manager.retry_count(existing) + (1 if existing else 0),
        })
    existing_manifest = existing_manifest or {}
    retry_history = existing_manifest.get("retry_history", []) if isinstance(existing_manifest.get("retry_history"), list) else []
    return {
        "schema_version": "1.1",
        "stage": "07B_character_appearance",
        "status": "needs_retry" if failures else "success",
        "appearances": rows,
        "appearance_manifest": {"schema_version": "1.1", "appearances": rows, "retry_history": retry_history},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures, "generated": generated, "skipped_existing_success": skipped},
    }
