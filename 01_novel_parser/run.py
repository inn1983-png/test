from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "01_novel_parser"
DISPLAY_NAME = "小说解析系统"
DESCRIPTION = "负责从小说文本中解析章节、剧情主线、冲突点、人物、场景、道具等基础信息。"
KEY_OUTPUT = "novel_analysis.json"


def read_novel_text() -> str:
    """Read optional novel input text for scaffold runs.

    Formal input convention:
    - workspace/.../input/novel.txt
    Standalone debug convention:
    - 01_novel_parser/input/novel.txt
    """
    novel_path = base_module.module_input_path(MODULE_NAME, "novel.txt")
    return io_utils.read_text(novel_path, default="").strip()


def build_scaffold_analysis(config: dict) -> dict:
    novel_text = read_novel_text()
    source_status = "input_found" if novel_text else "placeholder_input"
    preview = novel_text[:200]

    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source_status": source_status,
        "input_convention": "input/novel.txt",
        "novel": {
            "title": "未命名小说",
            "raw_text_preview": preview,
            "raw_text_length": len(novel_text),
        },
        "chapters": [
            {
                "chapter_id": "chapter_001",
                "title": "占位章节",
                "summary": "小说解析系统框架输出。后续将在此接入章节切分、事件提取、冲突点提取。",
                "paragraph_count": 0,
            }
        ],
        "events": [
            {
                "event_id": "event_001",
                "chapter_id": "chapter_001",
                "summary": "占位事件，用于打通 01→10 框架流程。",
                "conflict_level": "placeholder",
            }
        ],
        "candidate_characters": [],
        "candidate_scenes": [],
        "candidate_props": [],
        "notes": [
            "01 只提出角色、场景、道具候选，不直接写入 shared_assets。",
            "真实解析逻辑后续逐步接入。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_analysis(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="小说解析关键输出：章节、事件、候选角色、候选场景、候选道具。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"小说解析系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
