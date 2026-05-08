from backend.app.node_store import load_node, update_node


STYLE_FIX = "，电视剧电影真人写实风格，中国古代语境，电影级构图，真实自然光照"
NEGATIVE_FIX = "，现代物品，欧美人，现代服饰，眼镜，手表，拉链，电灯，电脑，手机，卡通，动漫，3D渲染，低质，模糊，性别错误，身份漂移"
VIDEO_FIX = "；保持人物身份、服装、场景、光源一致；只允许轻微自然运动；禁止新增人物和现代物品"


def repair_shot(node):
    node["image_prompt"] = (node.get("image_prompt") or "") + STYLE_FIX
    node["negative_prompt"] = (node.get("negative_prompt") or "") + NEGATIVE_FIX
    node["video_prompt"] = (node.get("video_prompt") or "") + VIDEO_FIX
    if len(node.get("cap", "")) > 120:
        node["repair_warning"] = "cap is long; consider manual split in UI"
    node["status"] = "waiting_image"
    return node


def repair_asset(node):
    node.setdefault("visual_lock", "stable identity, no drift, no modern elements")
    node["locked"] = True
    node["status"] = "done"
    return node


def repair_grid(node):
    node.setdefault("grid_mode", "grid_4")
    node["continuity_rule"] = "same grid keeps scene, light, costume and character identity stable"
    node["status"] = "waiting_grid"
    return node


def repair_node(project_id, node_id):
    node = load_node(project_id, node_id)
    node_type = node.get("type")
    if node_type == "shot":
        node = repair_shot(node)
    elif node_type in ["character_asset", "scene_asset", "prop_asset"]:
        node = repair_asset(node)
    elif node_type == "storyboard_grid":
        node = repair_grid(node)
    else:
        node["status"] = "waiting"
    node["repair_note"] = "repair applied by rule based repair agent"
    return update_node(project_id, node_id, node)
