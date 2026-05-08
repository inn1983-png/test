from backend.app.node_store import load_node, update_node


def run(project_id, node_id):
    load_node(project_id, node_id)
    output = "videos/" + node_id + ".mp4"
    return update_node(project_id, node_id, {"status": "done", "video_path": output})
