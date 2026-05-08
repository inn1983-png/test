from backend.app.node_store import load_node, update_node


def repair_node(project_id, node_id):
    node = load_node(project_id, node_id)
    note = "repair applied"
    if node.get("type") == "shot":
        node["negative_prompt"] = (node.get("negative_prompt") or "") + ", avoid identity drift"
    node["repair_note"] = note
    node["status"] = "waiting"
    return update_node(project_id, node_id, node)
