from __future__ import annotations

from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")

ROOT_DIR = Path(__file__).resolve().parents[1]


def bootstrap_module(module_name: str, display_name: str, description: str) -> dict[str, Any]:
    module_dir = ROOT_DIR / module_name
    input_dir = module_dir / "input"
    output_dir = module_dir / "output"

    io_utils.ensure_dir(input_dir)
    io_utils.ensure_dir(output_dir)

    config_path = module_dir / "module_config.json"
    config = io_utils.read_json(config_path, default=None)

    if config is None:
        config = {
            "module_name": module_name,
            "display_name": display_name,
            "description": description,
            "input_dir": str(input_dir.relative_to(ROOT_DIR)),
            "output_dir": str(output_dir.relative_to(ROOT_DIR)),
            "status": "scaffold"
        }
        io_utils.write_json(config_path, config)

    return config


def write_placeholder_output(module_name: str, data: dict[str, Any]) -> None:
    output_path = ROOT_DIR / module_name / "output" / "result.json"
    io_utils.write_json(output_path, data)
