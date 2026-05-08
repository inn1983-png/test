import json
import shutil
from pathlib import Path

from backend.app.project_store import ensure_project_dirs, utc_now

VALID_BUCKETS = {"pending", "running", "done", "failed"}


def tasks_root(project_id):
    return ensure_project_dirs(project_id) / "tasks"


def task_path(project_id, bucket, task_id):
    if bucket not in VALID_BUCKETS:
        raise ValueError("unknown task bucket")
    return tasks_root(project_id) / bucket / (task_id + ".json")


def save_task(project_id, task, bucket="pending"):
    task.setdefault("status", bucket)
    task.setdefault("retry_count", 0)
    task.setdefault("max_retry", 3)
    task.setdefault("created_at", utc_now())
    task["updated_at"] = utc_now()
    task_path(project_id, bucket, task["task_id"]).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task


def list_tasks(project_id):
    items = []
    for bucket in sorted(VALID_BUCKETS):
        for path in sorted((tasks_root(project_id) / bucket).glob("*.json")):
            items.append(json.loads(path.read_text(encoding="utf-8")))
    return items


def move_task(project_id, task_id, src_bucket, dst_bucket, changes=None):
    src = task_path(project_id, src_bucket, task_id)
    if not src.exists():
        raise FileNotFoundError(task_id)
    task = json.loads(src.read_text(encoding="utf-8"))
    if changes:
        task.update(changes)
    task["status"] = dst_bucket
    task["updated_at"] = utc_now()
    dst = task_path(project_id, dst_bucket, task_id)
    dst.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    src.unlink()
    return task


def enqueue_node_task(project_id, node_id, task_type, executor):
    task_id = "task_" + task_type + "_" + node_id
    return save_task(project_id, {
        "task_id": task_id,
        "node_id": node_id,
        "task_type": task_type,
        "executor": executor,
    })
