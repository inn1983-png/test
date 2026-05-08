import shutil

from backend.agents.asset_agent import generate_assets
from backend.agents.repair_agent import repair_node
from backend.agents.reviewer_agent import review_node
from backend.agents.storyboard_agent import generate_from_scripts
from backend.agents.writer_agent import generate as writer_generate
from backend.app.canvas_store import refresh_canvas
from backend.app.node_store import list_nodes, load_node, save_node, update_node
from backend.app.project_store import ensure_project_dirs, load_project, save_project
from backend.app.task_store import enqueue_node_task, list_tasks

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


def _set_stage(project_id, stage, progress):
    meta = load_project(project_id)
    meta["current_stage"] = stage
    meta["progress"] = progress
    save_project(project_id, meta)


def _require_nodes(project_id, node_type):
    nodes = list_nodes(project_id, node_type)
    if not nodes:
        raise ValueError(node_type + " not found")
    return nodes


def _has_active_task(project_id, node_id, task_type):
    for task in list_tasks(project_id):
        if task.get("node_id") == node_id and task.get("task_type") == task_type and task.get("status") in ["pending", "running"]:
            return True
    return False


def _enqueue_once(project_id, node_id, task_type, executor):
    if _has_active_task(project_id, node_id, task_type):
        return None
    return enqueue_node_task(project_id, node_id, task_type, executor)


def _action_response(project_id, action, **extra):
    result = {"action": action, "canvas": refresh_canvas(project_id)}
    result.update(extra)
    return result


def generate_script(project_id):
    sources = _require_nodes(project_id, "source_text")
    if list_nodes(project_id, "script_block"):
        return _action_response(project_id, "generate-script", generated=False, message="script_block already exists")
    writer_generate(project_id, sources[0].get("content", ""))
    _set_stage(project_id, "script", 20)
    return _action_response(project_id, "generate-script", generated=True, count=len(list_nodes(project_id, "script_block")))


def generate_assets_action(project_id):
    _require_nodes(project_id, "script_block")
    before = len([node for node in list_nodes(project_id) if node.get("type", "").endswith("_asset")])
    generate_assets(project_id)
    after = len([node for node in list_nodes(project_id) if node.get("type", "").endswith("_asset")])
    _set_stage(project_id, "assets", 35)
    return _action_response(project_id, "generate-assets", generated=True, count=max(0, after - before), total=after)


def generate_storyboard_action(project_id):
    _require_nodes(project_id, "script_block")
    if list_nodes(project_id, "shot"):
        return _action_response(project_id, "generate-storyboard", generated=False, message="shot already exists")
    generate_from_scripts(project_id)
    _set_stage(project_id, "storyboard", 50)
    return _action_response(project_id, "generate-storyboard", generated=True, shots=len(list_nodes(project_id, "shot")), grids=len(list_nodes(project_id, "storyboard_grid")))


def enqueue_images(project_id):
    shots = _require_nodes(project_id, "shot")
    enqueued = []
    skipped = []
    for shot in shots:
        if shot.get("image_path"):
            skipped.append({"node_id": shot["id"], "reason": "image_path already exists"})
            continue
        task = _enqueue_once(project_id, shot["id"], "image_generate", "image_executor")
        if task:
            update_node(project_id, shot["id"], {"status": "pending_image"})
            enqueued.append(task["task_id"])
        else:
            skipped.append({"node_id": shot["id"], "reason": "active image task already exists"})
    if enqueued:
        _set_stage(project_id, "images", 70)
    return _action_response(project_id, "enqueue-images", enqueued_count=len(enqueued), enqueued=enqueued, skipped=skipped)


def enqueue_grids(project_id):
    grids = _require_nodes(project_id, "storyboard_grid")
    enqueued = []
    skipped = []
    for grid in grids:
        if grid.get("grid_path"):
            skipped.append({"node_id": grid["id"], "reason": "grid_path already exists"})
            continue
        task = _enqueue_once(project_id, grid["id"], "grid_build", "grid_executor")
        if task:
            update_node(project_id, grid["id"], {"status": "pending_grid"})
            enqueued.append(task["task_id"])
        else:
            skipped.append({"node_id": grid["id"], "reason": "active grid task already exists"})
    if enqueued:
        _set_stage(project_id, "images", 75)
    return _action_response(project_id, "enqueue-grids", enqueued_count=len(enqueued), enqueued=enqueued, skipped=skipped)


def enqueue_audio(project_id):
    scripts = _require_nodes(project_id, "script_block")
    enqueued = []
    skipped = []
    for script in scripts:
        if script.get("audio_path"):
            skipped.append({"node_id": script["id"], "reason": "audio_path already exists"})
            continue
        task = _enqueue_once(project_id, script["id"], "audio_generate", "audio_executor")
        if task:
            update_node(project_id, script["id"], {"status": "pending_audio"})
            enqueued.append(task["task_id"])
        else:
            skipped.append({"node_id": script["id"], "reason": "active audio task already exists"})
    if enqueued:
        _set_stage(project_id, "audio", 82)
    return _action_response(project_id, "enqueue-audio", enqueued_count=len(enqueued), enqueued=enqueued, skipped=skipped)


def enqueue_video(project_id):
    grids = _require_nodes(project_id, "storyboard_grid")
    enqueued = []
    skipped = []
    for grid in grids:
        if not grid.get("grid_path"):
            skipped.append({"node_id": grid["id"], "reason": "grid_path not found"})
            continue
        if grid.get("video_path"):
            skipped.append({"node_id": grid["id"], "reason": "video_path already exists"})
            continue
        task = _enqueue_once(project_id, grid["id"], "video_generate", "video_executor")
        if task:
            update_node(project_id, grid["id"], {"status": "pending_video"})
            enqueued.append(task["task_id"])
        else:
            skipped.append({"node_id": grid["id"], "reason": "active video task already exists"})
    if enqueued:
        _set_stage(project_id, "video", 90)
    return _action_response(project_id, "enqueue-video", enqueued_count=len(enqueued), enqueued=enqueued, skipped=skipped)


def enqueue_final(project_id):
    task = _enqueue_once(project_id, "final", "final_assembly", "final_assembler")
    enqueued = [task["task_id"]] if task else []
    if task:
        _set_stage(project_id, "final", 98)
    return _action_response(project_id, "enqueue-final", enqueued_count=len(enqueued), enqueued=enqueued, skipped=[] if task else [{"node_id": "final", "reason": "active final task already exists"}])


PROJECT_ACTIONS = {
    "generate-script": generate_script,
    "generate-assets": generate_assets_action,
    "generate-storyboard": generate_storyboard_action,
    "enqueue-images": enqueue_images,
    "enqueue-grids": enqueue_grids,
    "enqueue-audio": enqueue_audio,
    "enqueue-video": enqueue_video,
    "enqueue-final": enqueue_final,
}


def run_project_action(project_id, action):
    if action not in PROJECT_ACTIONS:
        raise ValueError("unknown project action: " + action)
    return PROJECT_ACTIONS[action](project_id)


def _rerun_node(project_id, node_id):
    node = load_node(project_id, node_id)
    node_type = node.get("type")
    if node_type == "shot":
        update_node(project_id, node_id, {"status": "pending_image"})
        task = _enqueue_once(project_id, node_id, "image_generate", "image_executor")
        return task or {"task_id": "active image task already exists"}
    if node_type == "storyboard_grid":
        if node.get("grid_path"):
            update_node(project_id, node_id, {"status": "pending_video"})
            task = _enqueue_once(project_id, node_id, "video_generate", "video_executor")
            return task or {"task_id": "active video task already exists"}
        update_node(project_id, node_id, {"status": "pending_grid"})
        task = _enqueue_once(project_id, node_id, "grid_build", "grid_executor")
        return task or {"task_id": "active grid task already exists"}
    if node_type == "script_block":
        update_node(project_id, node_id, {"status": "pending_audio"})
        task = _enqueue_once(project_id, node_id, "audio_generate", "audio_executor")
        return task or {"task_id": "active audio task already exists"}
    raise ValueError("node type cannot be rerun: " + str(node_type))


def batch_node_action(project_id, action, node_ids):
    successes = []
    failures = []
    for node_id in node_ids or []:
        try:
            if action == "batch-review":
                result = review_node(project_id, node_id)
            elif action == "batch-repair":
                result = repair_node(project_id, node_id)
            elif action == "batch-rerun":
                result = _rerun_node(project_id, node_id)
            else:
                raise ValueError("unknown batch action: " + action)
            successes.append({"node_id": node_id, "result": result})
        except FileNotFoundError:
            failures.append({"node_id": node_id, "error": "node not found"})
        except Exception as exc:
            failures.append({"node_id": node_id, "error": str(exc)})
    return {
        "action": action,
        "success_count": len(successes),
        "failed_count": len(failures),
        "successes": successes,
        "failures": failures,
        "canvas": refresh_canvas(project_id),
    }


def lock_all_assets(project_id):
    locked = []
    for node in list_nodes(project_id):
        if node.get("type") in ["character_asset", "scene_asset", "prop_asset"]:
            update_node(project_id, node["id"], {"locked": True, "status": "locked"})
            locked.append(node["id"])
    return _action_response(project_id, "lock-assets", locked_count=len(locked), locked=locked)
