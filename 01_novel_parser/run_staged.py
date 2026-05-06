from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("01_novel_parser.core.stage_runner")

MODULE_NAME = "01_novel_parser"
DISPLAY_NAME = "小说解析系统"
DESCRIPTION = "负责通读小说、理解故事核心，并分阶段解析章节、事件图谱、全量候选资产、生产预判与故事质量控制信息。"
KEY_OUTPUT = "novel_analysis.json"
SCHEMA_VERSION = "1.2"


def read_novel_text() -> str:
    novel_path = base_module.module_input_path(MODULE_NAME, "novel.txt")
    return io_utils.read_text(novel_path, default="").strip()


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        novel_text = read_novel_text()
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)

        stage_result = stage_runner.run_scaffold_stages(novel_text, output_dir)
        data = stage_runner.merge_stage_outputs(novel_text, config, stage_result)

        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="小说解析关键输出：01A–01F 分阶段生成的全文理解、故事质量控制、事件图谱、生产预判、全量候选资产与原文证据链。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"小说解析系统已按 01A–01F 阶段框架运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "schema_version": SCHEMA_VERSION,
            "stage_mode": stage_result["stage_mode"],
            "stage_status": stage_result["stage_status"],
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
