import shutil
from pathlib import Path

from PIL import Image

from backend.app.node_store import save_node, load_node
from backend.app.project_store import ensure_project_dirs
from backend.executors.grid_executor import run


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_grid_executor_builds_png():
    project_id = "test_grid_executor"
    cleanup(project_id)
    project_dir = ensure_project_dirs(project_id)
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for index in range(1, 5):
        path = images_dir / f"shot_{index:03d}.png"
        Image.new("RGB", (64, 64), (index * 20, index * 20, index * 20)).save(path)
        save_node(project_id, {"id": f"shot_{index:03d}", "type": "shot", "status": "done", "image_path": "images/" + path.name})
    save_node(project_id, {"id": "grid_001", "type": "storyboard_grid", "status": "waiting_grid", "grid_mode": "grid_4", "shot_ids": ["shot_001", "shot_002", "shot_003", "shot_004"]})
    run(project_id, "grid_001")
    grid = load_node(project_id, "grid_001")
    assert grid["status"] == "done"
    assert (project_dir / grid["grid_path"]).exists()
    cleanup(project_id)
