import json

from backend.app.project_store import ensure_project_dirs, utc_now, load_project, save_project
from backend.app.node_store import save_node, list_nodes
from backend.app.status import DEFAULT_GRID_MODE, DEFAULT_STYLE_ID


def canvas_path(project_id):
    return ensure_project_dirs(project_id) / "canvas.json"


def build_canvas(project_id):
    items = []
    for node in list_nodes(project_id):
        node_id = node["id"]
        items.append({
            "id": node_id,
            "type": node["type"],
            "status": node.get("status", "pending"),
            "file": "nodes/" + node_id + ".json",
        })
    meta = load_project(project_id)
    return {
        "project_id": project_id,
        "chapter_id": "chapter_001",
        "style_id": DEFAULT_STYLE_ID,
        "grid_mode": DEFAULT_GRID_MODE,
        "status": "in_progress",
        "current_stage": meta.get("current_stage", "source"),
        "nodes": items,
        "edges": [],
        "updated_at": utc_now(),
    }


def load_canvas(project_id):
    path = canvas_path(project_id)
    if not path.exists():
        return save_canvas(project_id, build_canvas(project_id))
    return json.loads(path.read_text(encoding="utf-8"))


def save_canvas(project_id, canvas):
    canvas["updated_at"] = utc_now()
    canvas_path(project_id).write_text(json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")
    return canvas


def refresh_canvas(project_id):
    return save_canvas(project_id, build_canvas(project_id))


def seed_demo_nodes(project_id):
    save_node(project_id, {
        "id": "source_001",
        "type": "source_text",
        "status": "done",
        "title": "source text",
        "content": "Put novel source text here.",
    })
    save_node(project_id, {
        "id": "shot_001",
        "type": "shot",
        "status": "waiting",
        "cap": "Demo cap text from source.",
        "characters": ["protagonist"],
        "scene": "demo scene",
        "props": ["demo prop"],
        "image_prompt": "cinematic live action storyboard image",
        "negative_prompt": "modern object, cartoon, low quality",
    })
    save_node(project_id, {
        "id": "grid_001",
        "type": "storyboard_grid",
        "status": "waiting",
        "grid_mode": DEFAULT_GRID_MODE,
        "shot_ids": ["shot_001"],
    })
    meta = load_project(project_id)
    meta["current_stage"] = "storyboard"
    meta["progress"] = 20
    save_project(project_id, meta)
    return refresh_canvas(project_id)
