import json

from backend.app.project_store import ensure_project_dirs, utc_now
from backend.app.task_store import list_tasks, save_task


def task_file(project_id, bucket, task_id):
    return ensure_project_dirs(project_id) / "tasks" / bucket / (task_id + ".json")


def log_file(project_id, task_id):
    root = ensure_project_dirs(project_id) / "tasks" / "logs"
    root.mkdir(parents=True, exist_ok=True)
    return root / (task_id + ".log")


def append_log(project_id, task_id, message):
    path = log_file(project_id, task_id)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(old + "[" + utc_now() + "] " + message + "\n", encoding="utf-8")


def read_log(project_id, task_id):
    path = log_file(project_id, task_id)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def find_task(project_id, task_id):
    for task in list_tasks(project_id):
        if task.get("task_id") == task_id:
            return task
    raise FileNotFoundError(task_id)


def retry_task(project_id, task_id):
    task = find_task(project_id, task_id)
    for bucket in ["done", "failed", "running", "cancelled", "pending"]:
        path = task_file(project_id, bucket, task_id)
        if path.exists():
            path.unlink()
    task["status"] = "pending"
    task["retry_count"] = int(task.get("retry_count", 0)) + 1
    append_log(project_id, task_id, "retry")
    return save_task(project_id, task, "pending")


def cancel_task(project_id, task_id):
    task = find_task(project_id, task_id)
    for bucket in ["pending", "running", "done", "failed"]:
        path = task_file(project_id, bucket, task_id)
        if path.exists():
            path.unlink()
    task["status"] = "cancelled"
    path = task_file(project_id, "cancelled", task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    append_log(project_id, task_id, "cancelled")
    return task
