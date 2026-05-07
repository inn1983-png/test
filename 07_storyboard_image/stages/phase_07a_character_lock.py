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


def run(plan: dict[str, Any], characters: dict[str, Any], output_dir: str | Path, retry_options: dict[str, Any] | None = None, existing_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    cards = _character_map(characters)
    existing_rows = (existing_manifest or {}).get("character_locks", [])
    existing_by_key = retry_manager.existing_keyed(existing_rows if isinstance(existing_rows, list) else [], ["lock_key"])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    generated: list[str] = []
    skipped: list[str] = []
    for raw in plan.get("character_lock_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        lock_key = str(task.get("lock_key") or task.get("canonical_name") or task.get("task_id") or "")
        existing = existing_by_key.get(lock_key)
        if not retry_manager.should_run_item("character_lock", lock_key, existing, retry_options):
            if existing:
                rows.append(existing)
            continue
        task["task_type"] = "character_lock"
        task["workflow_config"] = workflow_router.route("character_lock")
        task["positive_prompt"] = prompt_builder.character_lock_prompt(task, cards.get(str(task.get("canonical_name"))))
        task["negative_prompt"] = prompt_builder.negative_prompt()
        task["output_basename"] = path_resolver.safe_key(str(task.get("lock_key") or task.get("canonical_name") or task.get("task_id")))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, "character_lock", task["output_basename"])
        if retry_manager.should_skip_success(existing, task["output_image_path"], retry_options):
            rows.append(retry_manager.mark_skipped_existing(existing))
            skipped.append(lock_key)
            continue
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
        else:
            generated.append(lock_key)
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
            "retry_count": retry_manager.retry_count(existing) + (1 if existing else 0),
        })
    existing_manifest = existing_manifest or {}
    retry_history = existing_manifest.get("retry_history", []) if isinstance(existing_manifest.get("retry_history"), list) else []
    return {
        "schema_version": "1.1",
        "stage": "07A_character_lock",
        "status": "needs_retry" if failures else "success",
        "character_locks": rows,
        "character_lock_manifest": {"schema_version": "1.1", "character_locks": rows, "retry_history": retry_history},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures, "generated": generated, "skipped_existing_success": skipped},
    }
