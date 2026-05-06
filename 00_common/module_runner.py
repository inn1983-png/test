from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def run_module(module_name: str) -> int:
    module_dir = ROOT_DIR / module_name
    run_file = module_dir / "run.py"

    if not run_file.exists():
        print(f"[SKIP] {module_name}: run.py not found")
        return 0

    print(f"[RUN] {module_name}")
    result = subprocess.run([sys.executable, str(run_file)], cwd=str(ROOT_DIR))

    if result.returncode != 0:
        print(f"[FAIL] {module_name}: return code {result.returncode}")
    else:
        print(f"[DONE] {module_name}")

    return result.returncode
