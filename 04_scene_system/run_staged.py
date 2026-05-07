from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("04_scene_system.core.stage_runner")
stage_cache = import_module("00_common.stage_cache")

MODULE_NAME = "04_scene_system"
DISPLAY_NAME = "场景库系统"
DESCRIPTION = "负责把 01 候选场景与 02 剧本场景使用信息标准化为稳定场景资产库。"
KEY_OUTPUT = "scenes.json"
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
        parser = argparse.ArgumentParser(description="04 scene system staged runner")
        stage_cache.add_resume_args(parser)
        args = parser.parse_args()

        force_stages = stage_cache.parse_force_stages(args.force_stage)
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        novel_analysis = _read_upstream("01_novel_parser", "novel_analysis.json")
        script = _read_upstream("02_script_writer", "script.json")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        stage_result = stage_runner.run_llm_stages(novel_analysis, script, output_dir, resume=args.resume, force=args.force, force_stages=force_stages)
        data = stage_runner.merge_stage_outputs(novel_analysis, script, config, stage_result)
        base_module.write_json_key_output(MODULE_NAME, KEY_OUTPUT, data, description="场景库关键输出：稳定场景名、别名、分级、参考图计划、复核报告、连续性规则与证据链。")
        base_module.write_json_key_output(
            MODULE_NAME,
            "scene_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "stage_mode": data.get("stage_mode"),
                "stage_status": data.get("stage_status", []),
                "final_revision_rounds": data.get("final_revision_rounds", []),
                "asset_review_report": data.get("asset_review_report", {}),
                "downstream_readiness_for_06": data.get("downstream_readiness_for_06", {}),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
            },
            description="场景库元信息：阶段状态、评分、复核、重跑记录与 schema 校验。",
        )
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
