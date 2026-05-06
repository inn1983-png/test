from __future__ import annotations

import gc
import subprocess
from typing import Iterable


def release_python_memory() -> None:
    """Release normal Python memory."""
    gc.collect()


def release_torch_cuda() -> None:
    """Release PyTorch CUDA cache if torch is installed and CUDA is available."""
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            print("[RESOURCE] torch CUDA cache released.")
    except Exception as exc:  # noqa: BLE001
        print(f"[RESOURCE] torch CUDA release skipped: {exc}")


def run_cleanup_commands(commands: Iterable[str]) -> None:
    """Run optional local cleanup commands after a module finishes.

    Example commands can be configured later for ComfyUI, local LLM servers,
    or model-specific unload endpoints/scripts.
    """
    for command in commands:
        if not command.strip():
            continue
        try:
            subprocess.run(command, shell=True, check=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[RESOURCE] cleanup command failed: {command} | {exc}")


def release_local_resources(module_name: str, cleanup_commands: Iterable[str] | None = None) -> None:
    """Unified cleanup hook for every independent subsystem.

    Rule:
    - A subsystem may load local LLM / image / video / vision models.
    - It must finish its task, write output files, then call this hook.
    - Other subsystems must not depend on this module's live memory state.
    """
    print(f"[RESOURCE] releasing resources for {module_name}...")
    release_python_memory()
    release_torch_cuda()
    if cleanup_commands:
        run_cleanup_commands(cleanup_commands)
    print(f"[RESOURCE] release finished for {module_name}.")
