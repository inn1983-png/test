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

LLM_TEXT_PHASE_MODULES = {
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
}
IMAGE_PHASE_MODULES = {"07_storyboard_image"}
AUDIO_PHASE_MODULES = {"08_audio"}
VIDEO_PHASE_MODULES = {"09_video"}
ASSEMBLY_PHASE_MODULES = {"10_final_assembly"}


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


def load_cleanup_commands(module_name: str, config_path: str | Path | None = None, command_group: str | None = None) -> list[str]:
    """Load enabled cleanup commands.

    Config format:

    ```json
    {
      "enabled": false,
      "global_commands": [],
      "module_commands": {
        "09_video": ["python scripts/unload_video_model.py"]
      },
      "phase_commands": {
        "release_llm_resources": ["python scripts/unload_llm.py"],
        "release_image_resources": [],
        "release_audio_resources": [],
        "release_video_resources": []
      }
    }
    ```

    Module-finish calls for 01-06 intentionally do not load external unload
    commands. Use phase-aware helpers when switching model families.
    """
    config = read_resource_config(config_path)
    if not config or not resource_commands_enabled(config):
        return []

    commands: list[str] = []
    if command_group:
        phase_commands = config.get("phase_commands", {})
        if isinstance(phase_commands, dict):
            commands.extend(_string_list(phase_commands.get(command_group)))
        return commands

    commands.extend(_string_list(config.get("global_commands")))
    module_commands = config.get("module_commands", {})
    if isinstance(module_commands, dict):
        commands.extend(_string_list(module_commands.get(module_name)))
    return commands


def run_cleanup_commands(commands: Iterable[str]) -> None:
    """Run optional local cleanup commands."""
    for command in commands:
        if not command.strip():
            continue
        try:
            print(f"[RESOURCE] cleanup command: {command}")
            subprocess.run(command, shell=True, check=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[RESOURCE] cleanup command failed: {command} | {exc}")


def _module_phase(module_name: str) -> str:
    if module_name in LLM_TEXT_PHASE_MODULES:
        return "LLM_TEXT_PHASE"
    if module_name in IMAGE_PHASE_MODULES:
        return "IMAGE_PHASE"
    if module_name in AUDIO_PHASE_MODULES:
        return "AUDIO_PHASE"
    if module_name in VIDEO_PHASE_MODULES:
        return "VIDEO_PHASE"
    if module_name in ASSEMBLY_PHASE_MODULES:
        return "ASSEMBLY_PHASE"
    return "UNKNOWN_PHASE"


def release_local_resources(module_name: str, cleanup_commands: Iterable[str] | None = None) -> None:
    """Module-finish cleanup hook.

    New phase rule:
    - 01-06 are continuous LLM_TEXT_PHASE modules. Gemma/local LLM should stay
      resident and must not be actively unloaded after each module.
    - 06 -> 07 is the explicit boundary where release_llm_resources() should be
      called before image generation / ComfyUI loads.
    - 07 image, 08 audio, 09 video can use model-family-specific release helpers.
    - 10 is normal assembly and does not need large model unload by default.
    """
    phase = _module_phase(module_name)
    print(f"[RESOURCE] module cleanup for {module_name} ({phase})...")
    release_python_memory()

    if module_name in LLM_TEXT_PHASE_MODULES:
        print("[RESOURCE] LLM_TEXT_PHASE: keep local LLM/Gemma resident; skip CUDA/model unload commands.")
        print(f"[RESOURCE] lightweight cleanup finished for {module_name}.")
        return

    if cleanup_commands is not None:
        commands = list(cleanup_commands)
    else:
        commands = load_cleanup_commands(module_name)

    if module_name in IMAGE_PHASE_MODULES | AUDIO_PHASE_MODULES | VIDEO_PHASE_MODULES:
        release_torch_cuda()

    if commands:
        run_cleanup_commands(commands)

    print(f"[RESOURCE] module cleanup finished for {module_name}.")


def release_llm_resources(config_path: str | Path | None = None) -> None:
    """Release local LLM resources at the 06 -> 07 boundary."""
    print("[RESOURCE] releasing LLM resources before image phase...")
    release_python_memory()
    release_torch_cuda()
    run_cleanup_commands(load_cleanup_commands("release_llm_resources", config_path, command_group="release_llm_resources"))
    print("[RESOURCE] LLM resource release finished.")


def release_image_resources(config_path: str | Path | None = None) -> None:
    """Release image generation / ComfyUI resources after 07 when needed."""
    print("[RESOURCE] releasing image resources...")
    release_python_memory()
    release_torch_cuda()
    run_cleanup_commands(load_cleanup_commands("release_image_resources", config_path, command_group="release_image_resources"))
    print("[RESOURCE] image resource release finished.")


def release_audio_resources(config_path: str | Path | None = None) -> None:
    """Release TTS / CosyVoice2 resources when VRAM pressure requires it."""
    print("[RESOURCE] releasing audio resources...")
    release_python_memory()
    release_torch_cuda()
    run_cleanup_commands(load_cleanup_commands("release_audio_resources", config_path, command_group="release_audio_resources"))
    print("[RESOURCE] audio resource release finished.")


def release_video_resources(config_path: str | Path | None = None) -> None:
    """Release LTX/video model resources after 09 when needed."""
    print("[RESOURCE] releasing video resources...")
    release_python_memory()
    release_torch_cuda()
    run_cleanup_commands(load_cleanup_commands("release_video_resources", config_path, command_group="release_video_resources"))
    print("[RESOURCE] video resource release finished.")
