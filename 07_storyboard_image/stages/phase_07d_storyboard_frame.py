from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")
prompt_builder = import_module("07_storyboard_image.core.prompt_builder")
path_resolver = import_module("07_storyboard_image.core.path_resolver")
workflow_router = import_module("07_storyboard_image.core.workflow_router")
retry_manager = import_module("07_storyboard_image.core.retry_manager")


def _frame_map(storyboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("frame_id")): item for item in storyboard.get("frames", []) or [] if isinstance(item, dict) and item.get("frame_id")}


def _appearance_map(appearance_manifest: dict[str, Any]) -> dict[str, str]:
    return {str(item.get("appearance_asset_key")): str(item.get("selected_image_path", "")) for item in appearance_manifest.get("appearances", []) or [] if isinstance(item, dict) and item.get("appearance_asset_key")}


def _reference_map(reference_manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in reference_manifest.get("scene_assets", []) or []:
        if isinstance(item, dict) and item.get("scene_key"):
            result[str(item["scene_key"])] = str(item.get("selected_image_path", ""))
    for item in reference_manifest.get("prop_assets", []) or []:
        if isinstance(item, dict) and item.get("prop_key"):
            result[str(item["prop_key"])] = str(item.get("selected_image_path", ""))
    return result


def _refs_for_task(task: dict[str, Any], appearance_paths: dict[str, str], reference_paths: dict[str, str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    scene_key = str(task.get("scene_ref_key", ""))
    if scene_key:
        refs.append({"kind": "scene", "key": scene_key, "path": reference_paths.get(scene_key, ""), "required": True})
    for app_key in task.get("appearance_asset_keys", []) or []:
        refs.append({"kind": "character_appearance", "key": app_key, "path": appearance_paths.get(str(app_key), ""), "required": True})
    for prop_key in task.get("prop_ref_keys", []) or []:
        refs.append({"kind": "prop", "key": prop_key, "path": reference_paths.get(str(prop_key), ""), "required": False})
    return refs


def run(
    plan: dict[str, Any],
    storyboard: dict[str, Any],
    appearance_manifest: dict[str, Any],
    reference_manifest: dict[str, Any],
    output_dir: str | Path,
    retry_options: dict[str, Any] | None = None,
    existing_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    frames = _frame_map(storyboard)
    appearance_paths = _appearance_map(appearance_manifest)
    reference_paths = _reference_map(reference_manifest)
    existing_rows = (existing_manifest or {}).get("images", [])
    existing_by_key = retry_manager.existing_keyed(existing_rows if isinstance(existing_rows, list) else [], ["frame_id"])
    ordered = sorted([task for task in plan.get("storyboard_frame_tasks", []) or [] if isinstance(task, dict)], key=lambda item: (not bool(item.get("is_anchor_frame")), item.get("sequence_index") or 0))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    generated: list[str] = []
    skipped: list[str] = []
    for raw in ordered:
        task = dict(raw)
        frame_id = str(task.get("frame_id", ""))
        existing = existing_by_key.get(frame_id)
        if not retry_manager.should_run_item("frame", frame_id, existing, retry_options):
            if existing:
                rows.append(existing)
            continue
        source_frame = frames.get(frame_id, {})
        task["task_type"] = "storyboard_frame"
        task["workflow_config"] = workflow_router.route("storyboard_frame")
        task["source_frame"] = source_frame
        task["reference_images"] = _refs_for_task(task, appearance_paths, reference_paths)
        task["positive_prompt"] = prompt_builder.storyboard_frame_prompt(task, source_frame)
        task["negative_prompt"] = prompt_builder.negative_prompt()
        task["output_basename"] = f"shot_{int(task.get('sequence_index') or 0):03d}" if isinstance(task.get("sequence_index"), int) else path_resolver.safe_key(frame_id)
        task["output_image_path"] = path_resolver.output_image_path(output_dir, "storyboard", task["output_basename"])
        if retry_manager.should_skip_success(existing, task["output_image_path"], retry_options):
            rows.append(retry_manager.mark_skipped_existing(existing))
            skipped.append(frame_id)
            continue
        result = client.submit_task(task, output_dir)
        status = result.get("status", "unknown")
        if status == "failed":
            failures.append(result)
        else:
            generated.append(frame_id)
        rows.append({
            "frame_id": frame_id,
            "sequence_index": task.get("sequence_index"),
            "source_frame_id": frame_id,
            "image_path": result.get("output_path"),
            "status": status,
            "execution_mode": result.get("execution_mode"),
            "scene_ref_key": task.get("scene_ref_key"),
            "appearance_asset_keys": task.get("appearance_asset_keys", []),
            "prop_ref_keys": task.get("prop_ref_keys", []),
            "is_anchor_frame": task.get("is_anchor_frame", False),
            "anchor_frame_id": task.get("anchor_frame_id"),
            "continuity_source_frame_id": task.get("continuity_source_frame_id"),
            "reference_images": task.get("reference_images", []),
            "scene": source_frame.get("scene", {}),
            "characters": source_frame.get("characters", []),
            "props": source_frame.get("props", []),
            "prompt_summary": {"positive_prompt_chars": len(task.get("positive_prompt", "")), "negative_prompt_chars": len(task.get("negative_prompt", "")), "output_basename": task.get("output_basename")},
            "execution_result": result,
            "retry_count": retry_manager.retry_count(existing) + (1 if existing else 0),
        })
    rows_sorted = sorted(rows, key=lambda item: item.get("sequence_index") or 0)
    image_manifest = {"schema_version": "1.1", "images": rows_sorted, "source_storyboard_schema_version": storyboard.get("schema_version")}
    retry_manager.append_retry_history(image_manifest, retry_options, generated, skipped)
    return {
        "schema_version": "1.1",
        "stage": "07D_storyboard_frame",
        "status": "needs_retry" if failures else "success",
        "images": rows_sorted,
        "image_manifest": image_manifest,
        "execution_summary": {"total": len(rows_sorted), "failed": len(failures), "failures": failures, "generated": generated, "skipped_existing_success": skipped},
    }
