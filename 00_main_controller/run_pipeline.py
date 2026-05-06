from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

io_utils = import_module("00_common.io_utils")
module_runner = import_module("00_common.module_runner")


def main() -> int:
    pipeline_config = io_utils.read_json(ROOT_DIR / "pipeline.json", default={})
    pipeline = pipeline_config.get("pipeline", [])

    if not pipeline:
        print("No pipeline configured. Please edit pipeline.json.")
        return 1

    for module_name in pipeline:
        code = module_runner.run_module(module_name)
        if code != 0:
            print(f"Pipeline stopped at: {module_name}")
            return code

    print("Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
