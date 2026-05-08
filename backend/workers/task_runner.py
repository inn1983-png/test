import importlib
import json
import time
import traceback

from backend.app.project_store import ensure_project_dirs, utc_now
from backend.app.task_store import move_task
from backend.app.task_actions import append_log
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
        started = time.time()
        append_log(project_id, task_id, "task started")
        move_task(project_id, task_id, "pending", "running", {"started_at": utc_now()})
        try:
            module_name = EXECUTOR_MAP[task["executor"]]
            append_log(project_id, task_id, "loading executor " + module_name)
            module = importlib.import_module(module_name)
            result = module.run(project_id, task["node_id"])
            duration = round(time.time() - started, 3)
            append_log(project_id, task_id, "task done in " + str(duration) + "s")
            move_task(project_id, task_id, "running", "done", {
                "result": result,
                "finished_at": utc_now(),
                "duration_seconds": duration,
            })
            done.append(task_id)
        except Exception as exc:
            duration = round(time.time() - started, 3)
            tb = traceback.format_exc()
            append_log(project_id, task_id, "task failed: " + str(exc))
            append_log(project_id, task_id, tb)
            move_task(project_id, task_id, "running", "failed", {
                "error": str(exc),
                "traceback": tb,
                "finished_at": utc_now(),
                "duration_seconds": duration,
            })
    refresh_canvas(project_id)
    return done
