from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")

MODULE_NAME = "01_novel_parser"
DISPLAY_NAME = "小说解析系统"
DESCRIPTION = "负责从小说文本中解析章节、剧情主线、冲突点、人物、场景、道具等基础信息。"


def main() -> int:
    config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
    base_module.write_placeholder_output(MODULE_NAME, {
        "module": MODULE_NAME,
        "status": "scaffold",
        "message": "小说解析系统骨架已运行，后续在此接入小说解析逻辑。",
        "config": config
    })
    print(f"{DISPLAY_NAME} finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
