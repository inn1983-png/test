import shutil
from pathlib import Path

from backend.app.workflow_store import save_workflow, load_workflow, list_workflows


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_save_and_load_workflow_json():
    project_id = "test_workflow_store"
    cleanup(project_id)
    saved = save_workflow(project_id, "image", "demo.json", {"1": {"inputs": {"text": "hello"}}})
    assert saved["category"] == "image"
    assert load_workflow(project_id, "image", "demo.json")["1"]["inputs"]["text"] == "hello"
    assert list_workflows(project_id)
    cleanup(project_id)
