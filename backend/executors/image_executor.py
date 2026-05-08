from backend.app.node_store import load_node, update_node


def run(project_id, node_id):
    load_node(project_id, node_id)
    output = "images/" + node_id + ".png"
    return update_node(project_id, node_id, {
        "status": "done",
        "image_path": output,
        "executor_note": "connect ComfyUI image workflow here",
    })
