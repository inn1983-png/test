from backend.app.canvas_store import load_canvas, seed_demo_nodes, refresh_canvas
from backend.app.node_store import list_nodes, update_node
from backend.app.task_store import enqueue_node_task, list_tasks
from backend.app.project_store import load_project, save_project
from backend.workers.task_runner import run_pending


STAGE_ORDER = ["source", "script", "assets", "storyboard", "images", "audio", "video", "final"]


def init_project(project_id):
    canvas = load_canvas(project_id)
    if not canvas.get("nodes"):
        canvas = seed_demo_nodes(project_id)
    return canvas


def has_pending_task(project_id, node_id, task_type):
    for task in list_tasks(project_id):
        if task.get("node_id") == node_id and task.get("task_type") == task_type and task.get("status") in ["pending", "running"]:
            return True
    return False


def next_step(project_id):
    init_project(project_id)
    shots = list_nodes(project_id, "shot")
    grids = list_nodes(project_id, "storyboard_grid")

    for shot in shots:
        if shot.get("status") in ["waiting", "waiting_image"] and not has_pending_task(project_id, shot["id"], "image_generate"):
            update_node(project_id, shot["id"], {"status": "pending_image"})
            enqueue_node_task(project_id, shot["id"], "image_generate", "image_executor")
            return refresh_canvas(project_id)

    for grid in grids:
        if grid.get("status") in ["waiting", "waiting_grid"] and not has_pending_task(project_id, grid["id"], "grid_build"):
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


def run_until_idle(project_id, max_steps=50):
    canvas = init_project(project_id)
    for _ in range(max_steps):
        next_step(project_id)
        run_pending(project_id)
        canvas = refresh_canvas(project_id)
        pending = [task for task in list_tasks(project_id) if task.get("status") in ["pending", "running"]]
        waiting_nodes = [node for node in list_nodes(project_id) if node.get("status") in ["waiting", "waiting_image", "waiting_grid"]]
        if not pending and not waiting_nodes:
            break
    return canvas
