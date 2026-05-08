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
    "00_style_system",
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly",
]

STYLE_PIPELINE_MODULE = "00_style_system"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate pipeline.json before running modules.")
    parser.add_argument("--pipeline", default="pipeline.json", help="Pipeline config file path.")
    parser.add_argument("--strict-order", action="store_true", help="Warn when modules are out of the recommended order.")
    return parser


def _module_has_entrypoint(module_dir: Path) -> bool:
    return (module_dir / "run_staged.py").exists() or (module_dir / "run.py").exists()


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

        if module_name in seen:
            ok = False
            messages.append(f"Duplicate module in pipeline: {module_name}")
        seen.add(module_name)

        if not module_dir.exists():
            ok = False
            messages.append(f"Module directory not found: {module_name}")
            continue

        if not _module_has_entrypoint(module_dir):
            ok = False
            messages.append(f"Module entrypoint not found: {module_name}/run_staged.py or {module_name}/run.py")

    if strict_order:
        order_index = {name: idx for idx, name in enumerate(DEFAULT_MODULE_ORDER)}
        filtered = [name for name in pipeline if name in order_index]
        expected = sorted(filtered, key=lambda name: order_index[name])
        if filtered != expected:
            messages.append("Pipeline order differs from recommended 00→10 order.")
            messages.append(f"Current: {filtered}")
            messages.append(f"Expected: {expected}")

    controller_modules = [
        name for name in pipeline
        if isinstance(name, str) and name[:3] == "00_" and name != STYLE_PIPELINE_MODULE
    ]
    if controller_modules:
        messages.append("Warning: pipeline usually should not include 00_* controller/common modules.")
        messages.append(f"Found: {controller_modules}")

    legacy_modules = [name for name in pipeline if name in {"03_character_library", "04_scene_library", "05_prop_library"}]
    if legacy_modules:
        ok = False
        messages.append("Legacy scaffold modules are not allowed in the active pipeline.")
        messages.append(f"Found: {legacy_modules}")

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
