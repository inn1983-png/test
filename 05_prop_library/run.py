from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "05_prop_library"
DISPLAY_NAME = "道具库系统"
DESCRIPTION = "负责提取、合并、标准化道具，并生成稳定的道具资产描述。"
KEY_OUTPUT = "props.json"


def build_scaffold_props(config: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": [
                "01_novel_parser.novel_analysis.json",
                "02_script_writer.script.json"
            ],
            "note": "当前为框架占位输出，后续接入道具提取、合并、标准化逻辑。",
        },
        "props": [
            {
                "prop_id": "prop_001",
                "name": "占位道具",
                "aliases": [],
                "prop_type": "placeholder",
                "visual_profile": "占位道具描述，后续由道具库系统生成稳定道具提示词。",
                "status": "placeholder",
            }
        ],
        "alias_map": {},
        "notes": [
            "同一道具只输出一次，后续可与 shared_assets/props 合并。",
            "道具系统只管理道具资产，不生成分镜。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_props(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="道具库关键输出：道具列表、别名映射、稳定道具描述。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"道具库系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
