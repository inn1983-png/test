from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")
artifact_registry = import_module("00_common.artifact_registry")

ROOT_DIR = Path(__file__).resolve().parents[1]


def get_runtime_module_dirs(module_name: str) -> tuple[Path, Path]:
    """Return input/output dirs for the current module.

    Formal pipeline runs write into workspace/.
    Standalone module debugging writes into module/input and module/output.
    """
    env_input = os.getenv("AI_DRAMA_MODULE_INPUT_DIR")
    env_output = os.getenv("AI_DRAMA_MODULE_OUTPUT_DIR")

    if env_input and env_output:
        input_dir = Path(env_input)
        output_dir = Path(env_output)
    else:
        module_dir = ROOT_DIR / module_name
        input_dir = module_dir / "input"
        output_dir = module_dir / "output"

    io_utils.ensure_dir(input_dir)
    io_utils.ensure_dir(output_dir)
    return input_dir, output_dir


def bootstrap_module(module_name: str, display_name: str, description: str) -> dict[str, Any]:
    module_dir = ROOT_DIR / module_name
    input_dir, output_dir = get_runtime_module_dirs(module_name)

    config_path = module_dir / "module_config.json"
    config = io_utils.read_json(config_path, default=None)

    if config is None:
        config = {
            "module_name": module_name,
            "display_name": display_name,
            "description": description,
            "status": "scaffold",
            "standalone_input_dir": str((module_dir / "input").relative_to(ROOT_DIR)),
            "standalone_output_dir": str((module_dir / "output").relative_to(ROOT_DIR)),
        }
        io_utils.write_json(config_path, config)

    runtime = {
        "runtime_input_dir": str(input_dir),
        "runtime_output_dir": str(output_dir),
        "run_id": os.getenv("AI_DRAMA_RUN_ID"),
        "mode": os.getenv("AI_DRAMA_MODE", "standalone"),
        "project_id": os.getenv("AI_DRAMA_PROJECT_ID"),
        "book_id": os.getenv("AI_DRAMA_BOOK_ID"),
        "chapter_id": os.getenv("AI_DRAMA_CHAPTER_ID"),
        "shared_assets_dir": os.getenv("AI_DRAMA_SHARED_ASSETS_DIR"),
        "global_memory_dir": os.getenv("AI_DRAMA_GLOBAL_MEMORY_DIR"),
    }

    return {**config, "runtime": runtime}


def register_output_artifact(
    module_name: str,
    artifact_name: str,
    path: str | Path,
    artifact_type: str,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    run_dir = os.getenv("AI_DRAMA_RUN_DIR")
    if not run_dir:
        return
    artifact_registry.register_artifact(
        run_dir=run_dir,
        module_name=module_name,
        artifact_name=artifact_name,
        path=path,
        artifact_type=artifact_type,
        description=description,
        metadata=metadata,
    )


def write_placeholder_output(module_name: str, data: dict[str, Any]) -> None:
    _, output_dir = get_runtime_module_dirs(module_name)
    output_path = output_dir / "result.json"
    io_utils.write_json(output_path, data)
    register_output_artifact(
        module_name=module_name,
        artifact_name="result",
        path=output_path,
        artifact_type="json",
        description="Scaffold placeholder output.",
    )


def module_output_path(module_name: str, filename: str) -> Path:
    _, output_dir = get_runtime_module_dirs(module_name)
    return output_dir / filename


def module_input_path(module_name: str, filename: str) -> Path:
    input_dir, _ = get_runtime_module_dirs(module_name)
    return input_dir / filename
