from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from importlib import import_module

workspace_manager = import_module("00_common.workspace_manager")
run_status = import_module("00_common.run_status")
module_contracts = import_module("00_common.module_contracts")
event_writer = import_module("00_common.event_writer")

ROOT_DIR = Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def resolve_run_file(module_dir: Path) -> Path:
    """Prefer staged entrypoint when a module provides it.

    This keeps existing modules compatible with run.py while allowing complex
    modules such as 01_novel_parser to use an internal staged workflow.
    """
    staged_file = module_dir / "run_staged.py"
    if staged_file.exists():
        return staged_file
    return module_dir / "run.py"


def run_module(module_name: str, context: Any | None = None) -> int:
    module_dir = ROOT_DIR / module_name
    run_file = resolve_run_file(module_dir)

    if not run_file.exists():
        print(f"[SKIP] {module_name}: run.py / run_staged.py not found")
        if context is not None:
            run_status.mark_skipped(context.run_dir, module_name, "run.py / run_staged.py not found")
        return 0

    env = os.environ.copy()
    if context is not None:
        env.update(workspace_manager.context_to_env(context, module_name))

    start_dt = datetime.now()
    start_time = start_dt.isoformat(timespec="seconds")
    if context is not None:
        run_status.mark_module(
            context.run_dir,
            module_name,
            status="running",
            start_time=start_time,
            message=f"module started: {run_file.name}",
        )
        event_writer.write_event(
            context.run_dir,
            module=module_name,
            event_type="module_started",
            message=f"module started: {run_file.name}",
            payload={"run_file": run_file.name},
        )

    print(f"[RUN] {module_name} via {run_file.name}")
    result = subprocess.run([sys.executable, str(run_file)], cwd=str(ROOT_DIR), env=env)

    end_dt = datetime.now()
    end_time = end_dt.isoformat(timespec="seconds")
    duration_seconds = round((end_dt - start_dt).total_seconds(), 3)

    if result.returncode != 0:
        print(f"[FAIL] {module_name}: return code {result.returncode}")
        if context is not None:
            run_status.mark_module(
                context.run_dir,
                module_name,
                status="failed",
                end_time=end_time,
                duration_seconds=duration_seconds,
                return_code=result.returncode,
                message=f"return code {result.returncode}",
            )
            event_writer.write_event(
                context.run_dir,
                module=module_name,
                event_type="module_finished",
                message=f"module failed: return code {result.returncode}",
                payload={"status": "failed", "return_code": result.returncode, "duration_seconds": duration_seconds},
            )
    else:
        output_messages: list[str] = []
        outputs_ok = True
        if context is not None:
            contracts = module_contracts.load_contracts()
            outputs_ok, output_messages = module_contracts.check_module_produces(
                context.run_dir,
                module_name,
                contracts,
            )
            for message in output_messages:
                print(f"[OUTPUT] {message}")

        if not outputs_ok:
            missing_messages = [message for message in output_messages if message.startswith("Missing required output")]
            message = "missing required outputs"
            if missing_messages:
                message = f"{message}: {'; '.join(missing_messages)}"
            print(f"[FAIL] {module_name}: {message}")
            if context is not None:
                run_status.mark_module(
                    context.run_dir,
                    module_name,
                    status="failed",
                    end_time=end_time,
                    duration_seconds=duration_seconds,
                    return_code=1,
                    message=message,
                )
                event_writer.write_event(
                    context.run_dir,
                    module=module_name,
                    event_type="module_finished",
                    message=message,
                    payload={"status": "failed", "return_code": 1, "duration_seconds": duration_seconds},
                )
            return 1

        print(f"[DONE] {module_name}")
        if context is not None:
            run_status.mark_module(
                context.run_dir,
                module_name,
                status="success",
                end_time=end_time,
                duration_seconds=duration_seconds,
                return_code=0,
                message=f"module finished: {run_file.name}",
            )
            event_writer.write_event(
                context.run_dir,
                module=module_name,
                event_type="module_finished",
                message=f"module finished: {run_file.name}",
                payload={"status": "success", "return_code": 0, "duration_seconds": duration_seconds},
            )

    return result.returncode
