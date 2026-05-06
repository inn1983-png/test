from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from importlib import import_module

workspace_manager = import_module("00_common.workspace_manager")

ROOT_DIR = Path(__file__).resolve().parents[1]


def run_module(module_name: str, context: Any | None = None) -> int:
    module_dir = ROOT_DIR / module_name
    run_file = module_dir / "run.py"

    if not run_file.exists():
        print(f"[SKIP] {module_name}: run.py not found")
        return 0

    env = os.environ.copy()
    if context is not None:
        env.update(workspace_manager.context_to_env(context, module_name))

    print(f"[RUN] {module_name}")
    result = subprocess.run([sys.executable, str(run_file)], cwd=str(ROOT_DIR), env=env)

    if result.returncode != 0:
        print(f"[FAIL] {module_name}: return code {result.returncode}")
    else:
        print(f"[DONE] {module_name}")

    return result.returncode
