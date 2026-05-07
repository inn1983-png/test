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
stage_runner = import_module("05_prop_system.core.stage_runner")

MODULE_NAME = "05_prop_system"
DISPLAY_NAME = "道具库系统"
DESCRIPTION = "负责把 01 候选道具与 02 剧本道具使用信息标准化为稳定道具资产库。"
KEY_OUTPUT = "props.json"
SCHEMA_VERSION = "1.2"


def _read_upstream(module_name: str, filename: str) -> dict:
    input_path = base_module.module_input_path(MODULE_NAME, filename)
    if not input_path.exists():
        run_dir = os.getenv("AI_DRAMA_RUN_DIR")
        if run_dir:
            fallback = Path(run_dir) / module_name / filename
            if fallback.exists():
                input_path = fallback
    data = io_utils.read_json(input_path, default=None)
    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"{MODULE_NAME} requires upstream {module_name}/{filename}.")
    return data


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        novel_analysis = _read_upstream("01_novel_parser", "novel_analysis.json")
        script = _read_upstream("02_script_writer", "script.json")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        stage_result = stage_runner.run_llm_stages(novel_analysis, script, output_dir)
        data = stage_runner.merge_stage_outputs(novel_analysis, script, config, stage_result)
        base_module.write_json_key_output(MODULE_NAME, KEY_OUTPUT, data, description="道具库关键输出：稳定道具名、别名、类型、归属角色、用途、外观、材质、风险说明与证据链。")
        base_module.write_json_key_output(MODULE_NAME, "prop_meta.json", {"module": MODULE_NAME, "schema_version": SCHEMA_VERSION, "status": data.get("status"), "stage_mode": data.get("stage_mode"), "stage_status": data.get("stage_status", []), "final_revision_rounds": data.get("final_revision_rounds", []), "quality_report": data.get("quality_report", {}), "schema_validation": data.get("schema_validation", {})}, description="道具库元信息：阶段状态、评分、重跑记录与 schema 校验。")
        base_module.write_placeholder_output(MODULE_NAME, {"module": MODULE_NAME, "status": data.get("status"), "message": f"道具库系统已按 05A–05D 阶段运行，关键输出已生成：{KEY_OUTPUT}", "key_output": KEY_OUTPUT, "schema_version": SCHEMA_VERSION, "stage_mode": stage_result["stage_mode"], "stage_status": stage_result["stage_status"], "config": config})
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
