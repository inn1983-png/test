from backend.app.node_store import load_node, update_node


def run(project_id, node_id):
    node = load_node(project_id, node_id)
    output = "grids/" + node_id + ".png"
    return update_node(project_id, node_id, {
        "status": "done",
        "grid_path": output,
        "shot_count": len(node.get("shot_ids", [])),
        "executor_note": "connect real grid image builder here",
    })
