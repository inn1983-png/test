from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "06_storyboard"
DISPLAY_NAME = "分镜系统"
DESCRIPTION = "负责把剧本拆成可生成的分镜，并绑定角色、场景、道具资产。"
KEY_OUTPUT = "storyboard.json"


def build_scaffold_storyboard(config: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": [
                "02_script_writer.script.json",
                "03_character_library.characters.json",
                "04_scene_library.scenes.json",
                "05_prop_library.props.json"
            ],
            "note": "当前为框架占位输出，后续接入分镜拆分、资产绑定、镜头衔接逻辑。",
        },
        "storyboard": [
            {
                "shot_id": "shot_001",
                "cap": "占位分镜文本",
                "theme": "占位",
                "desc_promopt": "占位分镜画面描述，用于打通 06→10 框架流程。古风电影感，人物与场景保持一致。",
                "characters": ["char_001"],
                "scene": "scene_001",
                "props": ["prop_001"],
                "camera": "中景，平视，稳定构图",
                "transition_to_next": "保持场景和人物位置连续",
            }
        ],
        "rules": {
            "cap_source": "真实版本必须来自原文或剧本文本连续片段，不得随意改写。",
            "image_strategy": "后续分镜图系统按单帧分镜生成，可再拼接为 4 宫格或 9 宫格参考图。",
        },
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_storyboard(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="分镜关键输出：shot 列表、cap、desc_promopt、角色/场景/道具绑定。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"分镜系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
