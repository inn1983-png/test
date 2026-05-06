from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")

MODULE_NAME = "02_script_writer"
DISPLAY_NAME = "剧本改编系统"
DESCRIPTION = "负责把小说内容改编成对白、OS、留白、动作、情绪明确的短剧剧本。"


def main() -> int:
    config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
    base_module.write_placeholder_output(MODULE_NAME, {
        "module": MODULE_NAME,
        "status": "scaffold",
        "message": "剧本改编系统骨架已运行，后续在此接入剧本改编提示词与生成逻辑。",
        "config": config
    })
    print(f"{DISPLAY_NAME} finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
