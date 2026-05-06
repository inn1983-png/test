from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

io_utils = import_module("00_common.io_utils")

DEFAULT_MODULE_ORDER = [
    "01_novel_parser",
    "02_script_writer",
    "03_character_library",
    "04_scene_library",
    "05_prop_library",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pipeline.json before running modules.")
    parser.add_argument("--pipeline", default="pipeline.json", help="Pipeline config file path.")
    parser.add_argument("--strict-order", action="store_true", help="Warn when modules are out of the recommended order.")
    return parser


def validate_pipeline_config(config: dict[str, Any], strict_order: bool = False) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    pipeline = config.get("pipeline")
    if not isinstance(pipeline, list) or not pipeline:
        return False, ["pipeline must be a non-empty list in pipeline.json"]

    seen: set[str] = set()
    for module_name in pipeline:
        if not isinstance(module_name, str):
            ok = False
            messages.append(f"Invalid module entry, expected string: {module_name!r}")
            continue

        module_dir = ROOT_DIR / module_name
        run_file = module_dir / "run.py"

        if module_name in seen:
            ok = False
            messages.append(f"Duplicate module in pipeline: {module_name}")
        seen.add(module_name)

        if not module_dir.exists():
            ok = False
            messages.append(f"Module directory not found: {module_name}")
            continue

        if not run_file.exists():
            ok = False
            messages.append(f"Module run.py not found: {module_name}/run.py")

    if strict_order:
        order_index = {name: idx for idx, name in enumerate(DEFAULT_MODULE_ORDER)}
        filtered = [name for name in pipeline if name in order_index]
        expected = sorted(filtered, key=lambda name: order_index[name])
        if filtered != expected:
            messages.append("Pipeline order differs from recommended 01→10 order.")
            messages.append(f"Current: {filtered}")
            messages.append(f"Expected: {expected}")

    unknown_modules = [name for name in pipeline if isinstance(name, str) and name.startswith("00_")]
    if unknown_modules:
        messages.append("Warning: pipeline usually should not include 00_* controller/common modules.")
        messages.append(f"Found: {unknown_modules}")

    if ok:
        messages.insert(0, "Pipeline validation passed.")
    else:
        messages.insert(0, "Pipeline validation failed.")

    return ok, messages


def main() -> int:
    args = build_parser().parse_args()
    pipeline_path = ROOT_DIR / args.pipeline

    if not pipeline_path.exists():
        print(f"Pipeline config not found: {pipeline_path}")
        return 1

    config = io_utils.read_json(pipeline_path, default={})
    ok, messages = validate_pipeline_config(config, strict_order=args.strict_order)

    for message in messages:
        print(message)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
