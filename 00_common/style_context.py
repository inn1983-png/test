from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
artifact_resolver = import_module("00_common.artifact_resolver")

STYLE_MODULE = "00_style_system"


def _resolve_style_file(run_dir: str | Path, filename: str) -> Path | None:
    run_path = Path(run_dir)

    resolved = artifact_resolver.resolve_key_output(run_path, STYLE_MODULE, filename)
    if resolved and Path(resolved).exists():
        return Path(resolved)

    artifact_paths = artifact_resolver.resolve_artifacts(
        run_dir=run_path,
        module_name=STYLE_MODULE,
        artifact_name=filename,
        limit=10,
    )
    for artifact_path in artifact_paths:
        if artifact_path.exists():
            return artifact_path

    fallback = artifact_resolver.fallback_module_file(run_path, STYLE_MODULE, filename)
    if fallback.exists():
        return fallback

    return None


def load_style_bible(run_dir: str | Path) -> dict[str, Any]:
    path = _resolve_style_file(run_dir, "style_bible.json")
    if not path:
        return {}
    data = io_utils.read_json(path, default={})
    return data if isinstance(data, dict) else {}


def load_style_text(run_dir: str | Path, filename: str) -> str:
    path = _resolve_style_file(run_dir, filename)
    if not path:
        return ""
    return io_utils.read_text(path, default="")


def load_style_prompt_prefix(run_dir: str | Path) -> str:
    return load_style_text(run_dir, "style_prompt_prefix.txt")


def load_image_style_lock(run_dir: str | Path) -> str:
    return load_style_text(run_dir, "image_style_lock.txt")


def load_video_style_lock(run_dir: str | Path) -> str:
    return load_style_text(run_dir, "video_style_lock.txt")


def load_style_negative_prompt(run_dir: str | Path) -> str:
    return load_style_text(run_dir, "style_negative_prompt.txt")


def build_style_summary_for_llm(run_dir: str | Path) -> str:
    bible = load_style_bible(run_dir)
    if not bible:
        return ""

    parts = [
        f"风格：{bible.get('display_name', bible.get('style_id', ''))}",
        f"时代：{bible.get('era', '')}",
        f"核心：{bible.get('core_style', '')}",
        f"叙事气质：{bible.get('story_tone', '')}",
        "镜头：" + "，".join(str(v) for v in bible.get("camera_language", [])),
        "光影：" + "，".join(str(v) for v in bible.get("lighting", [])),
        "色彩：" + "，".join(str(v) for v in bible.get("color_palette", [])),
    ]
    return "\n".join(part for part in parts if part.strip())
