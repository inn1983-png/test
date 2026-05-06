from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "02_script_writer"
DISPLAY_NAME = "剧本改编系统"
DESCRIPTION = "负责把小说内容改编成对白、OS、留白、动作、情绪明确的短剧剧本。"
KEY_OUTPUT = "script.json"


def build_scaffold_script(config: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": "01_novel_parser.novel_analysis.json",
            "note": "当前为框架占位输出，后续接入剧本改编提示词。",
        },
        "script_id": "script_001",
        "title": "占位短剧剧本",
        "format": "dialogue_os_blank",
        "segments": [
            {
                "segment_id": "seg_001",
                "type": "os",
                "speaker": "OS",
                "text": "这里是剧本改编系统占位旁白，用于打通 02→10 框架流程。",
                "emotion": "neutral",
                "visual_anchor": "占位画面锚点",
            },
            {
                "segment_id": "seg_002",
                "type": "blank",
                "duration_hint_seconds": 1.0,
                "text": "留白",
            },
        ],
        "notes": [
            "真实逻辑后续会把小说事件改编为对白 + OS + 留白。",
            "02 不直接修改角色、场景、道具资产库。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_script(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="剧本改编关键输出：对白、OS、留白、动作、情绪。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"剧本改编系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
