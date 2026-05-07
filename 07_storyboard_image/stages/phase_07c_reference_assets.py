from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")
prompt_builder = import_module("07_storyboard_image.core.prompt_builder")
path_resolver = import_module("07_storyboard_image.core.path_resolver")
workflow_router = import_module("07_storyboard_image.core.workflow_router")
retry_manager = import_module("07_storyboard_image.core.retry_manager")


def run(plan: dict[str, Any], output_dir: str | Path, retry_options: dict[str, Any] | None = None, existing_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    existing_rows = []
    if isinstance(existing_manifest, dict):
        existing_rows.extend(existing_manifest.get("scene_assets", []) or [])
        existing_rows.extend(existing_manifest.get("prop_assets", []) or [])
    existing_by_key = retry_manager.existing_keyed(existing_rows, ["scene_key", "prop_key", "asset_key"])
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    generated: list[str] = []
    skipped: list[str] = []
    for raw in plan.get("reference_asset_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        key = str(task.get("scene_key") or task.get("prop_key") or task.get("asset_key") or task.get("task_id") or "")
        existing = existing_by_key.get(key)
        if not retry_manager.should_run_item("reference_asset", key, existing, retry_options):
            if existing:
                rows.append(existing)
            continue
        task["task_type"] = "reference_asset"
        task["workflow_config"] = workflow_router.route("reference_asset")
        task["positive_prompt"] = prompt_builder.reference_asset_prompt(task)
        task["negative_prompt"] = prompt_builder.negative_prompt()
        category = "scene_reference" if task.get("asset_kind") == "scene" else "prop_reference"
        task["output_basename"] = path_resolver.safe_key(str(key))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, category, task["output_basename"])
        if retry_manager.should_skip_success(existing, task["output_image_path"], retry_options):
            rows.append(retry_manager.mark_skipped_existing(existing))
            skipped.append(key)
            continue
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
        else:
            generated.append(key)
        rows.append({
            "asset_kind": task.get("asset_kind"),
            "asset_key": key,
            "scene_key": task.get("scene_key"),
            "prop_key": task.get("prop_key"),
            "selected_image_path": result.get("output_path"),
            "source_frame_ids": task.get("source_frame_ids", []),
            "source_mode": "dry_run_or_generated",
            "status": status,
            "revision": 1,
            "execution_result": result,
            "retry_count": retry_manager.retry_count(existing) + (1 if existing else 0),
        })
    scene_assets = [item for item in rows if item.get("asset_kind") == "scene"]
    prop_assets = [item for item in rows if item.get("asset_kind") != "scene"]
    existing_manifest = existing_manifest or {}
    retry_history = existing_manifest.get("retry_history", []) if isinstance(existing_manifest.get("retry_history"), list) else []
    return {
        "schema_version": "1.1",
        "stage": "07C_reference_assets",
        "status": "needs_retry" if failures else "success",
        "reference_assets": rows,
        "reference_asset_manifest": {"schema_version": "1.1", "scene_assets": scene_assets, "prop_assets": prop_assets, "retry_history": retry_history},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures, "generated": generated, "skipped_existing_success": skipped},
    }
