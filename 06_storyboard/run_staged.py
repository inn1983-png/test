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
stage_runner = import_module("06_storyboard.core.stage_runner")

MODULE_NAME = "06_storyboard"
DISPLAY_NAME = "单帧分镜系统"
DESCRIPTION = "负责把 02 剧本与 03/04/05 稳定资产库转成只引用稳定资产名的单帧分镜 JSON。"
KEY_OUTPUT = "storyboard.json"
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
        script = _read_upstream("02_script_writer", "script.json")
        characters = _read_upstream("03_character_system", "characters.json")
        scenes = _read_upstream("04_scene_system", "scenes.json")
        props = _read_upstream("05_prop_system", "props.json")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        stage_result = stage_runner.run_llm_stages(script, characters, scenes, props, output_dir)
        data = stage_runner.merge_stage_outputs(script, characters, scenes, props, config, stage_result)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="06 关键输出：只引用 03/04/05 稳定资产名的单帧分镜 JSON，供 07 图片生成继续使用。",
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "storyboard_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "stage_mode": data.get("stage_mode"),
                "stage_status": data.get("stage_status", []),
                "final_revision_rounds": data.get("final_revision_rounds", []),
                "asset_availability_report": data.get("asset_availability_report", {}),
                "upstream_blocking_issues": data.get("upstream_blocking_issues", []),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
            },
            description="06 元信息：阶段状态、评分、资产阻塞、重跑记录与 schema 校验。",
        )
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
