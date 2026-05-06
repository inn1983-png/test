from __future__ import annotations

import gc
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RESOURCE_CONFIG = ROOT_DIR / "configs" / "local_resource_release.json"
ENABLE_RESOURCE_COMMANDS_ENV = "AI_DRAMA_ENABLE_RESOURCE_COMMANDS"
RESOURCE_CONFIG_ENV = "AI_DRAMA_RESOURCE_RELEASE_CONFIG"
_TRUE_VALUES = {"1", "true", "yes", "on"}


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


def get_resource_config_path() -> Path:
    """Return the configured local resource release config path."""
    custom_path = os.getenv(RESOURCE_CONFIG_ENV)
    if custom_path:
        return Path(custom_path)
    return DEFAULT_RESOURCE_CONFIG


def read_resource_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Read local resource release config.

    Missing config is allowed because some users may start with only Python / CUDA
    cache cleanup and add model-specific unload commands later.
    """
    path = Path(config_path) if config_path else get_resource_config_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[RESOURCE] release config skipped: {path} | {exc}")
        return {}
    if not isinstance(data, dict):
        print(f"[RESOURCE] release config skipped: {path} | root must be an object")
        return {}
    return data


def resource_commands_enabled(config: dict[str, Any]) -> bool:
    """Decide whether external cleanup commands may run.

    External commands are intentionally disabled by default. They can stop local
    model servers, call unload endpoints, or run user scripts, so they must be
    explicitly enabled.
    """
    env_value = os.getenv(ENABLE_RESOURCE_COMMANDS_ENV, "").strip().lower()
    if env_value in _TRUE_VALUES:
        return True
    return bool(config.get("enabled", False))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def load_cleanup_commands(module_name: str, config_path: str | Path | None = None) -> list[str]:
    """Load enabled cleanup commands for one module.

    Config format:

    ```json
    {
      "enabled": false,
      "global_commands": [],
      "module_commands": {
        "09_video": ["python scripts/unload_video_model.py"]
      }
    }
    ```
    """
    config = read_resource_config(config_path)
    if not config or not resource_commands_enabled(config):
        return []

    commands: list[str] = []
    commands.extend(_string_list(config.get("global_commands")))

    module_commands = config.get("module_commands", {})
    if isinstance(module_commands, dict):
        commands.extend(_string_list(module_commands.get(module_name)))

    return commands


def run_cleanup_commands(commands: Iterable[str]) -> None:
    """Run optional local cleanup commands after a module finishes.

    Example commands can be configured for ComfyUI, local LLM servers, video
    model unload scripts, TTS services, or other model-specific release actions.
    """
    for command in commands:
        if not command.strip():
            continue
        try:
            print(f"[RESOURCE] cleanup command: {command}")
            subprocess.run(command, shell=True, check=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[RESOURCE] cleanup command failed: {command} | {exc}")


def release_local_resources(module_name: str, cleanup_commands: Iterable[str] | None = None) -> None:
    """Unified cleanup hook for every independent subsystem.

    Rule:
    - A subsystem may load local LLM / image / video / vision / audio models.
    - It must finish its task, write output files, then call this hook.
    - Other subsystems must not depend on this module's live memory state.
    - External cleanup commands are loaded from config only when explicitly enabled.
    """
    print(f"[RESOURCE] releasing resources for {module_name}...")
    release_python_memory()
    release_torch_cuda()

    commands = list(cleanup_commands) if cleanup_commands is not None else load_cleanup_commands(module_name)
    if commands:
        run_cleanup_commands(commands)

    print(f"[RESOURCE] release finished for {module_name}.")
