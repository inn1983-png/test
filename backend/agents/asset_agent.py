from backend.app.node_store import save_node
from backend.app.canvas_store import refresh_canvas


def generate_default_assets(project_id):
    save_node(project_id, {
        "id": "character_protagonist",
        "type": "character_asset",
        "status": "done",
        "name": "protagonist",
        "gender": "unknown",
        "visual_lock": "single consistent protagonist",
        "locked": True,
    })
    save_node(project_id, {
        "id": "scene_default",
        "type": "scene_asset",
        "status": "done",
        "name": "default scene",
        "visual_lock": "consistent scene and lighting",
        "forbidden": ["modern objects", "western props"],
        "locked": True,
    })
    save_node(project_id, {
        "id": "prop_default",
        "type": "prop_asset",
        "status": "done",
        "name": "default prop",
        "visual_lock": "clear prop identity",
        "locked": True,
    })
    return refresh_canvas(project_id)
