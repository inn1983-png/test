from pathlib import Path

from backend.app.node_store import load_node, update_node
from backend.app.settings_store import load_settings
from backend.executors.comfyui_client import run_workflow, extract_images_from_history


def _workflow_name(settings):
    value = settings.get("image_workflow", "")
    return Path(value).name if value else "storyboard_image.json"


def _build_inputs(settings, node):
    mapping = settings.get("workflow_mappings", {}).get("image", {})
    prompt_node = mapping.get("prompt_node")
    negative_node = mapping.get("negative_node")
    if not prompt_node:
        return None, "Missing image workflow mapping: prompt_node"
    inputs = {
        prompt_node: {mapping.get("prompt_input", "text"): node.get("image_prompt", "")}
    }
    if negative_node:
        inputs[negative_node] = {mapping.get("negative_input", "text"): node.get("negative_prompt", "")}
    return inputs, None


def run(project_id, node_id):
    node = load_node(project_id, node_id)
    settings = load_settings(project_id)
    inputs, error = _build_inputs(settings, node)
    if error:
        return update_node(project_id, node_id, {"status": "needs_review", "error": error})
    try:
        result = run_workflow(project_id, "image", _workflow_name(settings), inputs)
        images = extract_images_from_history(result)
        patch = {"status": "done", "comfyui_result": result}
        if images:
            patch["comfyui_output"] = images[0]
            patch["image_path"] = images[0]
        else:
            patch["status"] = "needs_review"
            patch["error"] = "ComfyUI finished but no image output was parsed from history."
        return update_node(project_id, node_id, patch)
    except Exception as exc:
        return update_node(project_id, node_id, {
            "status": "failed",
            "error": str(exc),
            "executor_note": "Upload image workflow JSON and configure image workflow mapping in Settings.",
        })
