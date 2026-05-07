from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_WORKFLOW_TYPES = {
    "character_lock": {
        "description": "文生图角色定妆照 workflow",
        "workflow_path": "",
        "positive_node_id": "",
        "negative_node_id": "",
        "output_prefix_node_id": "",
        "positive_input": "text",
        "negative_input": "text",
        "output_prefix_input": "filename_prefix",
    },
    "character_appearance": {
        "description": "图生图角色换装/造型 workflow",
        "workflow_path": "",
        "positive_node_id": "",
        "negative_node_id": "",
        "output_prefix_node_id": "",
        "positive_input": "text",
        "negative_input": "text",
        "output_prefix_input": "filename_prefix",
    },
    "reference_asset": {
        "description": "场景/道具参考图 workflow",
        "workflow_path": "",
        "positive_node_id": "",
        "negative_node_id": "",
        "output_prefix_node_id": "",
        "positive_input": "text",
        "negative_input": "text",
        "output_prefix_input": "filename_prefix",
    },
    "storyboard_frame": {
        "description": "正式单帧分镜图 workflow",
        "workflow_path": "",
        "positive_node_id": "",
        "negative_node_id": "",
        "output_prefix_node_id": "",
        "positive_input": "text",
        "negative_input": "text",
        "output_prefix_input": "filename_prefix",
    },
}


def load_mapping() -> dict[str, Any]:
    path = os.getenv("AI_DRAMA_COMFYUI_WORKFLOW_MAPPING", "").strip()
    if not path:
        return DEFAULT_WORKFLOW_TYPES
    file_path = Path(path)
    if not file_path.exists():
        raise RuntimeError(f"workflow mapping not found: {file_path}")
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("workflow mapping root must be object")
    merged = {**DEFAULT_WORKFLOW_TYPES}
    for key, value in data.items():
        if isinstance(value, dict):
            merged[key] = {**merged.get(key, {}), **value}
    return merged


def route(task_type: str) -> dict[str, Any]:
    mapping = load_mapping()
    return mapping.get(task_type, mapping.get("storyboard_frame", {}))
