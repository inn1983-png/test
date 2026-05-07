from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")
prompt_builder = import_module("07_storyboard_image.core.prompt_builder")
path_resolver = import_module("07_storyboard_image.core.path_resolver")
workflow_router = import_module("07_storyboard_image.core.workflow_router")


def _character_map(characters: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("canonical_name")): item for item in characters.get("characters", []) or [] if isinstance(item, dict) and item.get("canonical_name")}


def _lock_map(lock_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("lock_key")): item for item in lock_manifest.get("character_locks", []) or [] if isinstance(item, dict) and item.get("lock_key")}


def run(plan: dict[str, Any], characters: dict[str, Any], lock_manifest: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    cards = _character_map(characters)
    locks = _lock_map(lock_manifest)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for raw in plan.get("appearance_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        task["task_type"] = "character_appearance"
        task["workflow_config"] = workflow_router.route("character_appearance")
        base_lock = locks.get(str(task.get("base_lock_key")), {})
        task["base_lock_image_path"] = base_lock.get("selected_image_path", "")
        task["positive_prompt"] = prompt_builder.appearance_prompt(task, cards.get(str(task.get("canonical_name"))))
        task["negative_prompt"] = prompt_builder.negative_prompt()
        task["output_basename"] = path_resolver.safe_key(str(task.get("appearance_asset_key") or task.get("task_id")))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, "character_appearance", task["output_basename"])
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
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
        })
    return {
        "schema_version": "1.1",
        "stage": "07B_character_appearance",
        "status": "needs_retry" if failures else "success",
        "appearances": rows,
        "appearance_manifest": {"schema_version": "1.1", "appearances": rows},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures},
    }
