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


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        base_module.write_placeholder_output(MODULE_NAME, {"module": MODULE_NAME, "status": "scaffold", "message": "分镜图生成系统骨架已运行。", "config": config})
        print(f"{DISPLAY_NAME} finished.")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
