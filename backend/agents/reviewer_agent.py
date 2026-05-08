from backend.app.node_store import load_node, update_node


MODERN_FORBIDDEN = ["手机", "电脑", "电灯", "汽车", "眼镜", "手表", "拉链"]
PROMPT_REQUIRED = ["真人写实", "中国古代", "电影"]


def review_shot(node):
    issues = []
    cap = node.get("cap", "")
    prompt = node.get("image_prompt", "")
    negative = node.get("negative_prompt", "")
    if not cap:
        issues.append("missing cap")
    if len(cap) > 120:
        issues.append("cap too long for one shot")
    if not prompt:
        issues.append("missing image prompt")
    for word in PROMPT_REQUIRED:
        if word not in prompt:
            issues.append("image prompt missing required style word: " + word)
    for word in MODERN_FORBIDDEN:
        if word in prompt and word not in negative:
            issues.append("modern forbidden word not covered by negative prompt: " + word)
    if not node.get("video_prompt"):
        issues.append("missing video prompt")
    return issues


def review_asset(node):
    issues = []
    if not node.get("name"):
        issues.append("missing asset name")
    if not node.get("visual_lock"):
        issues.append("missing visual lock")
    if node.get("type") == "character_asset" and "年轻" in node.get("name", ""):
        issues.append("character name may contain age split")
    return issues


def review_grid(node):
    issues = []
    if not node.get("shot_ids"):
        issues.append("grid has no shots")
    if node.get("grid_mode") not in ["grid_4", "grid_6", "grid_9"]:
        issues.append("unknown grid mode")
    return issues


def review_node(project_id, node_id):
    node = load_node(project_id, node_id)
    node_type = node.get("type")
    if node_type == "shot":
        issues = review_shot(node)
    elif node_type in ["character_asset", "scene_asset", "prop_asset"]:
        issues = review_asset(node)
    elif node_type == "storyboard_grid":
        issues = review_grid(node)
    else:
        issues = []
    score = max(0, 100 - len(issues) * 15)
    return update_node(project_id, node_id, {
        "review": {"score": score, "issues": issues},
        "status": "done" if score >= 80 else "needs_review",
    })
