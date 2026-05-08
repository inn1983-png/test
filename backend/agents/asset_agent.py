import re

from backend.app.node_store import save_node, list_nodes
from backend.app.canvas_store import refresh_canvas


ROLE_SUFFIX = ["捕头", "捕快", "县令", "师爷", "夫人", "小姐", "公子", "老爷", "掌柜", "衙役", "官差", "将军", "王爷", "皇帝"]
SCENE_WORDS = ["衙门", "街", "院", "堂", "牢", "府", "宫", "城门", "酒楼", "客栈", "书房", "祠堂", "荒野"]
PROP_WORDS = ["刀", "剑", "令牌", "皂服", "银子", "竹简", "毛笔", "灯", "碗", "卷宗", "锁链", "马车"]


def normalize_id(prefix, name):
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", name).strip("_")
    return prefix + "_" + cleaned


def extract_characters(text):
    found = set()
    for suffix in ROLE_SUFFIX:
        for match in re.findall(r"[\u4e00-\u9fff]{1,4}" + suffix, text):
            found.add(match)
    if "你" in text:
        found.add("主角")
    return sorted(found) or ["主角"]


def extract_scenes(text):
    scenes = []
    for word in SCENE_WORDS:
        if word in text:
            scenes.append("古代" + word)
    return sorted(set(scenes)) or ["古代室内场景"]


def extract_props(text):
    props = [word for word in PROP_WORDS if word in text]
    return sorted(set(props))


def generate_assets(project_id):
    content = "\n".join(node.get("content", "") for node in list_nodes(project_id) if node.get("type") in ["source_text", "story_segment", "script_block"])
    characters = extract_characters(content)
    scenes = extract_scenes(content)
    props = extract_props(content)

    for name in characters:
        save_node(project_id, {
            "id": normalize_id("character", name),
            "type": "character_asset",
            "status": "done",
            "name": name,
            "gender": "unknown",
            "visual_lock": "single consistent Chinese period drama character, no age split, no identity drift",
            "costume_lock": "ancient Chinese costume, no modern accessories",
            "negative_prompt": "modern clothes, western face, glasses, watch, zipper, cartoon, 3d render",
            "locked": True,
        })

    for name in scenes:
        save_node(project_id, {
            "id": normalize_id("scene", name),
            "type": "scene_asset",
            "status": "done",
            "name": name,
            "era": "ancient_china",
            "visual_lock": "Chinese ancient live action cinematic scene, consistent light and layout",
            "forbidden": ["modern object", "electric light", "phone", "computer", "western interior"],
            "locked": True,
        })

    for name in props:
        save_node(project_id, {
            "id": normalize_id("prop", name),
            "type": "prop_asset",
            "status": "done",
            "name": name,
            "visual_lock": "clear ancient Chinese prop, stable shape and material",
            "locked": True,
        })

    return refresh_canvas(project_id)


def generate_default_assets(project_id):
    return generate_assets(project_id)
