from backend.app.canvas_store import load_canvas, seed_demo_nodes, refresh_canvas
from backend.app.node_store import list_nodes, update_node
from backend.app.task_store import enqueue_node_task, list_tasks
from backend.app.project_store import load_project, save_project
from backend.workers.task_runner import run_pending
from backend.agents.writer_agent import generate as writer_generate
from backend.agents.asset_agent import generate_assets
from backend.agents.storyboard_agent import generate_from_scripts
from backend.agents.reviewer_agent import review_node


STAGE_ORDER = ["source", "script", "assets", "storyboard", "review", "images", "audio", "video", "final"]


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


def set_stage(project_id, stage, progress):
    meta = load_project(project_id)
    meta["current_stage"] = stage
    meta["progress"] = progress
    save_project(project_id, meta)


def ensure_script(project_id):
    scripts = list_nodes(project_id, "script_block")
    if scripts:
        return False
    sources = list_nodes(project_id, "source_text")
    text = sources[0].get("content", "") if sources else "Put novel source text here."
    writer_generate(project_id, text)
    set_stage(project_id, "script", 20)
    return True


def ensure_assets(project_id):
    if list_nodes(project_id, "character_asset") and list_nodes(project_id, "scene_asset"):
        return False
    generate_assets(project_id)
    set_stage(project_id, "assets", 35)
    return True


def ensure_storyboard(project_id):
    if list_nodes(project_id, "shot"):
        return False
    generate_from_scripts(project_id)
    set_stage(project_id, "storyboard", 50)
    return True


def ensure_review(project_id):
    reviewed = False
    for node in list_nodes(project_id):
        if node.get("type") in ["shot", "storyboard_grid", "character_asset", "scene_asset", "prop_asset"] and not node.get("review"):
            review_node(project_id, node["id"])
            reviewed = True
    if reviewed:
        set_stage(project_id, "review", 60)
    return reviewed


def enqueue_media_tasks(project_id):
    for shot in list_nodes(project_id, "shot"):
        if shot.get("status") in ["waiting", "waiting_image", "done", "needs_review"] and not shot.get("image_path") and not has_pending_task(project_id, shot["id"], "image_generate"):
            update_node(project_id, shot["id"], {"status": "pending_image"})
            enqueue_node_task(project_id, shot["id"], "image_generate", "image_executor")
            set_stage(project_id, "images", 70)
            return True
    for grid in list_nodes(project_id, "storyboard_grid"):
        if grid.get("status") in ["waiting", "waiting_grid", "done", "needs_review"] and not grid.get("grid_path") and not has_pending_task(project_id, grid["id"], "grid_build"):
            update_node(project_id, grid["id"], {"status": "pending_grid"})
            enqueue_node_task(project_id, grid["id"], "grid_build", "grid_executor")
            set_stage(project_id, "images", 75)
            return True
    return False


def next_step(project_id):
    init_project(project_id)
    if ensure_script(project_id):
        return refresh_canvas(project_id)
    if ensure_assets(project_id):
        return refresh_canvas(project_id)
    if ensure_storyboard(project_id):
        return refresh_canvas(project_id)
    if ensure_review(project_id):
        return refresh_canvas(project_id)
    if enqueue_media_tasks(project_id):
        return refresh_canvas(project_id)
    set_stage(project_id, "final", 100)
    return refresh_canvas(project_id)


def run_until_idle(project_id, max_steps=80):
    canvas = init_project(project_id)
    for _ in range(max_steps):
        next_step(project_id)
        run_pending(project_id)
        canvas = refresh_canvas(project_id)
        pending = [task for task in list_tasks(project_id) if task.get("status") in ["pending", "running"]]
        nodes = list_nodes(project_id)
        unfinished = [n for n in nodes if n.get("status") in ["waiting", "waiting_image", "waiting_grid", "pending_image", "pending_grid"]]
        if not pending and not unfinished:
            break
    return canvas
