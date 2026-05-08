import json
from pathlib import Path

from backend.app.project_store import ensure_project_dirs, utc_now

NODE_TYPES = {
    "source_text", "story_segment", "script_block", "character_asset", "scene_asset",
    "prop_asset", "shot", "storyboard_grid", "audio_segment", "video_clip"
}


def nodes_dir(project_id):
    return ensure_project_dirs(project_id) / "nodes"


def node_path(project_id, node_id):
    return nodes_dir(project_id) / (node_id + ".json")


def save_node(project_id, node):
    if node.get("type") not in NODE_TYPES:
        raise ValueError("unknown node type")
    node.setdefault("status", "pending")
    node.setdefault("created_at", utc_now())
    node["updated_at"] = utc_now()
    node_path(project_id, node["id"]).write_text(json.dumps(node, ensure_ascii=False, indent=2), encoding="utf-8")
    return node


def load_node(project_id, node_id):
    return json.loads(node_path(project_id, node_id).read_text(encoding="utf-8"))


def update_node(project_id, node_id, changes):
    node = load_node(project_id, node_id)
    node.update(changes)
    return save_node(project_id, node)


def list_nodes(project_id, node_type=None):
    items = []
    for path in sorted(nodes_dir(project_id).glob("*.json")):
        node = json.loads(path.read_text(encoding="utf-8"))
        if node_type is None or node.get("type") == node_type:
            items.append(node)
    return items
