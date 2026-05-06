from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "07_storyboard_image"
DISPLAY_NAME = "分镜图生成系统"
DESCRIPTION = "负责读取分镜、角色图、场景图、道具图，生成单帧分镜图。"
KEY_OUTPUT = "image_manifest.json"


def build_scaffold_image_manifest(config: dict) -> dict:
    image_placeholder = base_module.write_text_key_output(
        MODULE_NAME,
        "shot_001.png",
        "PLACEHOLDER IMAGE FILE. Real image generation will replace this file.",
        description="占位分镜图文件，用于框架闭环测试。",
        artifact_type="image",
        metadata={"shot_id": "shot_001", "placeholder": True},
    )
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": "06_storyboard.storyboard.json",
            "note": "当前为框架占位输出，后续接入 ComfyUI 分镜图生成逻辑。",
        },
        "images": [
            {
                "shot_id": "shot_001",
                "image_id": "image_001",
                "path": str(image_placeholder),
                "type": "placeholder_png",
                "prompt_source": "06_storyboard.storyboard.json",
                "status": "placeholder",
            }
        ],
        "grid_strategy": {
            "enabled_later": True,
            "rule": "后续可按 1-4, 4-7, 7-10 的重叠策略拼接四宫格。",
        },
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_image_manifest(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="分镜图关键输出：分镜图清单、路径、shot 绑定关系。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"分镜图生成系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
