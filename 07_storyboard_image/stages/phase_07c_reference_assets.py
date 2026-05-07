from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")
prompt_builder = import_module("07_storyboard_image.core.prompt_builder")
path_resolver = import_module("07_storyboard_image.core.path_resolver")
workflow_router = import_module("07_storyboard_image.core.workflow_router")


def run(plan: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for raw in plan.get("reference_asset_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        task = dict(raw)
        task["task_type"] = "reference_asset"
        task["workflow_config"] = workflow_router.route("reference_asset")
        task["positive_prompt"] = prompt_builder.reference_asset_prompt(task)
        task["negative_prompt"] = prompt_builder.negative_prompt()
        key = task.get("scene_key") or task.get("prop_key") or task.get("asset_key") or task.get("task_id")
        category = "scene_reference" if task.get("asset_kind") == "scene" else "prop_reference"
        task["output_basename"] = path_resolver.safe_key(str(key))
        task["output_image_path"] = path_resolver.output_image_path(output_dir, category, task["output_basename"])
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
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
        })
    scene_assets = [item for item in rows if item.get("asset_kind") == "scene"]
    prop_assets = [item for item in rows if item.get("asset_kind") != "scene"]
    return {
        "schema_version": "1.1",
        "stage": "07C_reference_assets",
        "status": "needs_retry" if failures else "success",
        "reference_assets": rows,
        "reference_asset_manifest": {"schema_version": "1.1", "scene_assets": scene_assets, "prop_assets": prop_assets},
        "execution_summary": {"total": len(rows), "failed": len(failures), "failures": failures},
    }
