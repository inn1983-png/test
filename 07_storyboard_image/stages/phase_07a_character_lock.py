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


def run(plan: dict[str, Any], characters: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    cards = _character_map(characters)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for raw in plan.get("character_lock_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        task["task_type"] = "character_lock"
        task["workflow_config"] = workflow_router.route("character_lock")
        task["positive_prompt"] = prompt_builder.character_lock_prompt(task, cards.get(str(task.get("canonical_name"))))
        task["negative_prompt"] = prompt_builder.negative_prompt()
        task["output_basename"] = path_resolver.safe_key(str(task.get("lock_key") or task.get("canonical_name") or task.get("task_id")))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, "character_lock", task["output_basename"])
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
        rows.append({
            "lock_key": task.get("lock_key"),
            "canonical_name": task.get("canonical_name"),
            "asset_level": task.get("asset_level"),
            "needs_fixed_face": task.get("needs_fixed_face"),
            "selected_image_path": result.get("output_path"),
            "candidate_images": [result.get("output_path")] if result.get("output_path") else [],
            "source_frame_ids": task.get("source_frame_ids", []),
            "downstream_appearance_keys": task.get("downstream_appearance_keys", []),
            "status": status,
            "revision": 1,
            "execution_result": result,
            "prompt_summary": {"positive_prompt_chars": len(task.get("positive_prompt", "")), "negative_prompt_chars": len(task.get("negative_prompt", ""))},
        })
    return {
        "schema_version": "1.1",
        "stage": "07A_character_lock",
        "status": "needs_retry" if failures else "success",
        "character_locks": rows,
        "character_lock_manifest": {"schema_version": "1.1", "character_locks": rows},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures},
    }
