import shutil
from pathlib import Path

from backend.app.project_store import ensure_project_dirs, load_project, save_project
from backend.app.node_store import save_node
from backend.app.canvas_store import refresh_canvas

GENERATED_PREFIXES = (
    "segment_", "script_", "character_", "scene_", "prop_", "shot_", "grid_", "audio_", "video_"
)


def reset_project_generated_nodes(project_id):
    project_dir = ensure_project_dirs(project_id)
    nodes_dir = project_dir / "nodes"
    for path in nodes_dir.glob("*.json"):
        if path.stem == "source_001" or path.stem.startswith(GENERATED_PREFIXES):
            path.unlink()
    for bucket in ["pending", "running", "done", "failed", "cancelled"]:
        task_dir = project_dir / "tasks" / bucket
        for path in task_dir.glob("*.json"):
            path.unlink()
    for media_dir in ["images", "grids", "audio", "videos", "final"]:
        target = project_dir / media_dir
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)


def import_source_text(project_id, title, content):
    reset_project_generated_nodes(project_id)
    save_node(project_id, {
        "id": "source_001",
        "type": "source_text",
        "status": "done",
        "title": title or project_id,
        "content": content or "",
    })
    meta = load_project(project_id)
    meta["title"] = title or project_id
    meta["current_stage"] = "source"
    meta["progress"] = 5
    save_project(project_id, meta)
    return refresh_canvas(project_id)
