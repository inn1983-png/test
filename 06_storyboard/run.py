from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")

MODULE_NAME = "06_storyboard"
DISPLAY_NAME = "分镜系统"
DESCRIPTION = "负责把剧本拆成可生成的分镜，并绑定角色、场景、道具资产。"


def main() -> int:
    config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
    base_module.write_placeholder_output(MODULE_NAME, {"module": MODULE_NAME, "status": "scaffold", "message": "分镜系统骨架已运行。", "config": config})
    print(f"{DISPLAY_NAME} finished.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
