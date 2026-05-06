from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "03_character_library"
DISPLAY_NAME = "角色库系统"
DESCRIPTION = "负责提取、合并、去重角色，并生成稳定的角色资产描述。"
KEY_OUTPUT = "characters.json"


def build_scaffold_characters(config: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": [
                "01_novel_parser.novel_analysis.json",
                "02_script_writer.script.json"
            ],
            "note": "当前为框架占位输出，后续接入角色提取、合并、去重逻辑。",
        },
        "characters": [
            {
                "character_id": "char_001",
                "name": "占位角色",
                "aliases": [],
                "gender": "unknown",
                "role_type": "placeholder",
                "visual_profile": "占位角色形象描述，后续由角色库系统生成稳定外观。",
                "voice_profile": "占位音色描述，后续供音频系统使用。",
                "status": "placeholder",
            }
        ],
        "alias_map": {},
        "notes": [
            "同一角色只输出一次，不按年龄段拆分。",
            "长篇模式下后续会与 shared_assets/characters 合并，但本框架版本只产出章节候选结果。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_characters(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="角色库关键输出：角色列表、别名映射、稳定角色描述。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"角色库系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
