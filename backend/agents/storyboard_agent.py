from backend.app.node_store import save_node
from backend.app.canvas_store import refresh_canvas
from backend.app.status import DEFAULT_GRID_MODE


def generate_shots(project_id, caps):
    shot_ids = []
    for index, cap in enumerate(caps, start=1):
        shot_id = "shot_" + str(index).zfill(3)
        shot_ids.append(shot_id)
        save_node(project_id, {
            "id": shot_id,
            "type": "shot",
            "status": "waiting",
            "cap": cap,
            "characters": [],
            "scene": "",
            "props": [],
            "image_prompt": "",
            "negative_prompt": "",
            "video_prompt": "",
            "locked": False,
        })
    for group_index in range(0, len(shot_ids), 4):
        grid_no = group_index // 4 + 1
        save_node(project_id, {
            "id": "grid_" + str(grid_no).zfill(3),
            "type": "storyboard_grid",
            "status": "waiting",
            "grid_mode": DEFAULT_GRID_MODE,
            "shot_ids": shot_ids[group_index:group_index + 4],
        })
    return refresh_canvas(project_id)
