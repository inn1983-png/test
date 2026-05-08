from backend.app.node_store import save_node
from backend.app.canvas_store import refresh_canvas


def generate(project_id, source_text):
    save_node(project_id, {
        "id": "script_001",
        "type": "script_block",
        "status": "done",
        "source_ref": "source_001",
        "content": source_text,
        "dialogue": [],
        "os": [],
        "beats": ["setup", "conflict", "turn"],
    })
    return refresh_canvas(project_id)
