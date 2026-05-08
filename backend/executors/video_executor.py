from pathlib import Path

from backend.app.node_store import load_node, update_node
from backend.app.settings_store import load_settings
from backend.executors.comfyui_client import run_workflow


def _workflow_name(settings):
    value = settings.get("video_workflow", "")
    return Path(value).name if value else "ltx23_grid_video.json"


def run(project_id, node_id):
    node = load_node(project_id, node_id)
    settings = load_settings(project_id)
    output = "videos/" + node_id + ".mp4"
    try:
        result = run_workflow(project_id, "video", _workflow_name(settings), {
            "PROMPT_NODE": {"text": node.get("video_prompt", node.get("image_prompt", ""))},
            "IMAGE_NODE": {"image": node.get("grid_path", node.get("image_path", ""))},
        })
        return update_node(project_id, node_id, {
            "status": "done",
            "video_path": output,
            "comfyui_result": result,
        })
    except Exception as exc:
        return update_node(project_id, node_id, {
            "status": "failed",
            "video_path": output,
            "error": str(exc),
            "executor_note": "Upload video workflow JSON or adjust node ids in local workflow mapping.",
        })
