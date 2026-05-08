from backend.app.canvas_store import load_canvas, seed_demo_nodes, refresh_canvas
from backend.app.node_store import list_nodes, update_node
from backend.app.task_store import enqueue_node_task
from backend.app.project_store import load_project, save_project


STAGE_ORDER = ["source", "script", "assets", "storyboard", "images", "audio", "video", "final"]


def init_project(project_id):
    canvas = load_canvas(project_id)
    if not canvas.get("nodes"):
        canvas = seed_demo_nodes(project_id)
    return canvas


def next_step(project_id):
    canvas = init_project(project_id)
    shots = list_nodes(project_id, "shot")
    grids = list_nodes(project_id, "storyboard_grid")

    for shot in shots:
        if shot.get("status") == "waiting":
            update_node(project_id, shot["id"], {"status": "pending_image"})
            enqueue_node_task(project_id, shot["id"], "image_generate", "image_executor")
            return refresh_canvas(project_id)

    for grid in grids:
        if grid.get("status") == "waiting":
            update_node(project_id, grid["id"], {"status": "pending_grid"})
            enqueue_node_task(project_id, grid["id"], "grid_build", "grid_executor")
            return refresh_canvas(project_id)

    meta = load_project(project_id)
    current = meta.get("current_stage", "storyboard")
    if current in STAGE_ORDER:
        idx = STAGE_ORDER.index(current)
        if idx + 1 < len(STAGE_ORDER):
            meta["current_stage"] = STAGE_ORDER[idx + 1]
            meta["progress"] = min(100, int((idx + 2) / len(STAGE_ORDER) * 100))
            save_project(project_id, meta)

    return refresh_canvas(project_id)


def run_until_idle(project_id, max_steps=20):
    canvas = init_project(project_id)
    for _ in range(max_steps):
        before = canvas.get("updated_at")
        canvas = next_step(project_id)
        after = canvas.get("updated_at")
        if before == after:
            break
    return canvas
