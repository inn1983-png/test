import re

from backend.app.node_store import save_node, list_nodes
from backend.app.canvas_store import refresh_canvas
from backend.app.settings_store import load_settings
from backend.app.status import DEFAULT_GRID_MODE


SPLIT_RE = re.compile(r"(?<=[。！？!?；;，,])")


def split_cap_text(text, max_len=80):
    parts = [p.strip() for p in SPLIT_RE.split(text) if p.strip()]
    caps = []
    buf = ""
    for part in parts:
        if not buf:
            buf = part
        elif len(buf) + len(part) <= max_len:
            buf += part
        else:
            caps.append(buf)
            buf = part
    if buf:
        caps.append(buf)
    return caps or [text]


def infer_shot_assets(project_id, cap):
    characters = [n for n in list_nodes(project_id, "character_asset") if n.get("name") and n.get("name") in cap]
    scenes = [n for n in list_nodes(project_id, "scene_asset") if n.get("name") and n.get("name").replace("古代", "") in cap]
    props = [n for n in list_nodes(project_id, "prop_asset") if n.get("name") and n.get("name") in cap]
    return {
        "characters": [n.get("name") for n in characters] or (["主角"] if "你" in cap else []),
        "scene": scenes[0].get("name") if scenes else "古代室内场景",
        "props": [n.get("name") for n in props],
    }


def build_image_prompt(cap, assets):
    people = "，".join(assets.get("characters", [])) or "无明确人物"
    props = "，".join(assets.get("props", [])) or "无明确道具"
    return "电视剧电影真人写实风格，中国古代语境，" + assets.get("scene", "古代场景") + "，人物：" + people + "，道具：" + props + "，画面严格表现原文连续片段：" + cap + "，自然真实光照，电影级构图，清晰细节，情绪凝重。"


def build_video_prompt(cap):
    return "保持分镜图人物身份、服装、场景、光源一致；只做轻微自然运动和镜头推进；画面内容严格对应 cap：" + cap


def build_negative_prompt():
    return "现代物品，欧美人，现代服饰，眼镜，手表，拉链，电灯，电脑，手机，卡通，动漫，3D渲染，游戏风，插画，低质，模糊，畸形，多肢，多人错位，性别错误"


def choose_grid_mode(project_id):
    settings = load_settings(project_id)
    return settings.get("default_grid_mode") or DEFAULT_GRID_MODE


def grid_size(mode):
    if mode == "grid_9":
        return 9
    if mode == "grid_6":
        return 6
    return 4


def generate_from_scripts(project_id):
    caps = []
    for node in list_nodes(project_id, "script_block"):
        caps.extend(split_cap_text(node.get("content", "")))
    if not caps:
        for node in list_nodes(project_id, "source_text"):
            caps.extend(split_cap_text(node.get("content", "")))
    return generate_shots(project_id, caps)


def generate_shots(project_id, caps):
    shot_ids = []
    for index, cap in enumerate(caps, start=1):
        shot_id = "shot_" + str(index).zfill(3)
        shot_ids.append(shot_id)
        assets = infer_shot_assets(project_id, cap)
        save_node(project_id, {
            "id": shot_id,
            "type": "shot",
            "status": "waiting_image",
            "cap": cap,
            "cap_rule": "strict continuous source text; do not rewrite cap",
            "characters": assets["characters"],
            "scene": assets["scene"],
            "props": assets["props"],
            "camera": "medium close-up or slow push-in, stable cinematic shot",
            "image_prompt": build_image_prompt(cap, assets),
            "negative_prompt": build_negative_prompt(),
            "video_prompt": build_video_prompt(cap),
            "locked": False,
        })
    mode = choose_grid_mode(project_id)
    size = grid_size(mode)
    for group_index in range(0, len(shot_ids), size):
        grid_no = group_index // size + 1
        save_node(project_id, {
            "id": "grid_" + str(grid_no).zfill(3),
            "type": "storyboard_grid",
            "status": "waiting_grid",
            "grid_mode": mode,
            "shot_ids": shot_ids[group_index:group_index + size],
            "continuity_rule": "same grid keeps scene, light, costume and character identity stable",
        })
    return refresh_canvas(project_id)
