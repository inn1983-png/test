import importlib
import json

from backend.app.project_store import ensure_project_dirs
from backend.app.task_store import move_task
from backend.app.canvas_store import refresh_canvas

EXECUTOR_MAP = {
    "image_executor": "backend.executors.image_executor",
    "grid_executor": "backend.executors.grid_executor",
    "audio_executor": "backend.executors.audio_executor",
    "video_executor": "backend.executors.video_executor",
    "final_assembler": "backend.executors.final_assembler",
}


def run_pending(project_id, limit=100):
    root = ensure_project_dirs(project_id) / "tasks" / "pending"
    done = []
    for path in sorted(root.glob("*.json"))[:limit]:
        task = json.loads(path.read_text(encoding="utf-8"))
        task_id = task["task_id"]
        move_task(project_id, task_id, "pending", "running")
        try:
            module_name = EXECUTOR_MAP[task["executor"]]
            module = importlib.import_module(module_name)
            result = module.run(project_id, task["node_id"])
            move_task(project_id, task_id, "running", "done", {"result": result})
            done.append(task_id)
        except Exception as exc:
            move_task(project_id, task_id, "running", "failed", {"error": str(exc)})
    refresh_canvas(project_id)
    return done
