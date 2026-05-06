from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "04_scene_library"
DISPLAY_NAME = "场景库系统"
DESCRIPTION = "负责提取、合并、标准化场景，并生成稳定的场景资产描述。"
KEY_OUTPUT = "scenes.json"


def build_scaffold_scenes(config: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": [
                "01_novel_parser.novel_analysis.json",
                "02_script_writer.script.json"
            ],
            "note": "当前为框架占位输出，后续接入场景提取、合并、标准化逻辑。",
        },
        "scenes": [
            {
                "scene_id": "scene_001",
                "name": "占位场景",
                "aliases": [],
                "time_period": "unknown",
                "location_type": "placeholder",
                "visual_profile": "占位场景描述，后续由场景库系统生成稳定古风环境提示词。",
                "lighting": "neutral",
                "status": "placeholder",
            }
        ],
        "alias_map": {},
        "notes": [
            "同一场景只输出一次，后续可与 shared_assets/scenes 合并。",
            "场景系统只管理场景资产，不生成分镜。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_scenes(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="场景库关键输出：场景列表、别名映射、稳定场景描述。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"场景库系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
