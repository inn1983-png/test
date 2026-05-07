from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path
from importlib import import_module
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("07_storyboard_image.core.stage_runner")

MODULE_NAME = "07_storyboard_image"
DISPLAY_NAME = "分镜图生成系统"
DESCRIPTION = "负责把 06 单帧分镜转成可执行图片任务，调用本地 ComfyUI 生成分镜图，并输出 image_manifest.json。"
KEY_OUTPUT = "image_manifest.json"
SCHEMA_VERSION = "1.0"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 07 storyboard image stage.")
    parser.add_argument("--retry-scope", choices=["all", "failed", "frame", "character_lock", "appearance", "reference_asset"], default=os.getenv("AI_DRAMA_IMAGE_RETRY_SCOPE", "all"))
    parser.add_argument("--frame-id", default=os.getenv("AI_DRAMA_IMAGE_RETRY_FRAME_ID", ""))
    parser.add_argument("--asset-key", default=os.getenv("AI_DRAMA_IMAGE_RETRY_ASSET_KEY", ""))
    parser.add_argument("--force", action="store_true", default=_env_bool("AI_DRAMA_IMAGE_RETRY_FORCE", False))
    return parser


def _read_upstream(module_name: str, filename: str) -> dict[str, Any]:
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


def _read_optional_upstream(module_name: str, filename: str) -> dict[str, Any]:
    try:
        return _read_upstream(module_name, filename)
    except Exception:
        return {}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.retry_scope == "frame" and not args.frame_id:
        raise SystemExit("--retry-scope frame requires --frame-id")
    if args.retry_scope in {"character_lock", "appearance", "reference_asset"} and not args.asset_key:
        raise SystemExit(f"--retry-scope {args.retry_scope} requires --asset-key")
    retry_options = {
        "retry_scope": args.retry_scope,
        "frame_id": args.frame_id,
        "asset_key": args.asset_key,
        "force": args.force,
    }
    try:
        resource_manager.release_llm_resources()
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        storyboard = _read_upstream("06_storyboard", "storyboard.json")
        characters = _read_optional_upstream("03_character_system", "characters.json")
        scenes = _read_optional_upstream("04_scene_system", "scenes.json")
        props = _read_optional_upstream("05_prop_system", "props.json")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        stage_result = stage_runner.run_image_stages(storyboard, characters, scenes, props, output_dir, retry_options=retry_options)
        data = stage_runner.merge_stage_outputs(storyboard, characters, scenes, props, config, stage_result, output_dir)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="07 关键输出：分镜图生成清单、参考图任务、ComfyUI 执行结果和每帧图片路径。",
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "image_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "stage_mode": data.get("stage_mode"),
                "execution_mode": data.get("execution_mode"),
                "stage_status": data.get("stage_status", []),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
                "missing_references": data.get("missing_references", []),
            },
            description="07 元信息：图片阶段状态、缺失参考图、执行模式、评分与 schema 校验。",
        )
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
