from __future__ import annotations

import os
import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("02_script_writer.core.stage_runner")

MODULE_NAME = "02_script_writer"
DISPLAY_NAME = "剧本改编系统"
DESCRIPTION = "负责把 01 小说解析结果分阶段改编成音频驱动、单帧分镜友好的短剧剧本。"
KEY_OUTPUT = "script.json"
SCHEMA_VERSION = "1.1"


def read_novel_analysis() -> dict:
    input_path = base_module.module_input_path(MODULE_NAME, "novel_analysis.json")
    if not input_path.exists():
        run_dir = os.getenv("AI_DRAMA_RUN_DIR")
        if run_dir:
            fallback = Path(run_dir) / "01_novel_parser" / "novel_analysis.json"
            if fallback.exists():
                input_path = fallback
    data = io_utils.read_json(input_path, default=None)
    if not isinstance(data, dict) or not data:
        raise RuntimeError("02_script_writer requires upstream 01_novel_parser/novel_analysis.json.")
    return data


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        novel_analysis = read_novel_analysis()
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)

        stage_result = stage_runner.run_llm_stages(novel_analysis, output_dir)
        data = stage_runner.merge_stage_outputs(novel_analysis, config, stage_result)

        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="剧本改编关键输出：02A–02F 分阶段生成的改编蓝图、剧本结构、语音行计划、正式剧本、生产标注与质量总检。",
        )
        base_module.write_text_key_output(
            MODULE_NAME,
            "script.txt",
            data.get("script_text", ""),
            description="可读剧本文本：对白、OS、留白、动作、情绪，包含音频行标记。",
            artifact_type="text",
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "script_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "stage_mode": data.get("stage_mode"),
                "stage_status": data.get("stage_status", []),
                "final_revision_rounds": data.get("final_revision_rounds", []),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
            },
            description="剧本改编元信息：阶段状态、评分、重跑记录与 schema 校验。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": data.get("status"),
            "message": f"剧本改编系统已按 02A–02F 阶段运行，关键输出已生成：{KEY_OUTPUT}",
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
