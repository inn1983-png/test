from backend.app.node_store import load_node, update_node


def run(project_id, node_id):
    load_node(project_id, node_id)
    return update_node(project_id, node_id, {
        "status": "done",
        "audio_path": "audio/" + node_id + ".wav",
        "subtitle_path": "audio/" + node_id + ".srt",
    })
