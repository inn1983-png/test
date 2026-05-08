from pathlib import Path

from backend.app.node_store import load_node, update_node
from backend.app.settings_store import load_settings
from backend.executors.comfyui_client import run_workflow


def _workflow_name(settings):
    value = settings.get("image_workflow", "")
    return Path(value).name if value else "storyboard_image.json"


def run(project_id, node_id):
    node = load_node(project_id, node_id)
    settings = load_settings(project_id)
    output = "images/" + node_id + ".png"
    try:
        result = run_workflow(project_id, "image", _workflow_name(settings), {
            "PROMPT_NODE": {"text": node.get("image_prompt", "")},
            "NEGATIVE_NODE": {"text": node.get("negative_prompt", "")},
        })
        return update_node(project_id, node_id, {
            "status": "done",
            "image_path": output,
            "comfyui_result": result,
        })
    except Exception as exc:
        return update_node(project_id, node_id, {
            "status": "failed",
            "image_path": output,
            "error": str(exc),
            "executor_note": "Upload image workflow JSON or adjust node ids in local workflow mapping.",
        })
