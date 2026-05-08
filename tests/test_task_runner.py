import shutil
from pathlib import Path

from backend.app.task_actions import read_log
from backend.app.task_store import list_tasks, save_task
from backend.workers.task_runner import run_pending


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_task_runner_failure_writes_traceback_and_duration():
    project_id = "test_task_runner"
    cleanup(project_id)
    save_task(project_id, {
        "task_id": "task_bad_executor",
        "node_id": "missing",
        "task_type": "bad",
        "executor": "missing_executor",
    })

    run_pending(project_id)

    failed = [task for task in list_tasks(project_id) if task["task_id"] == "task_bad_executor"][0]
    assert failed["status"] == "failed"
    assert "traceback" in failed
    assert "duration_seconds" in failed
    assert "Traceback" in read_log(project_id, "task_bad_executor")
    cleanup(project_id)
