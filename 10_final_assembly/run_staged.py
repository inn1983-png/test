from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("10_final_assembly.core.stage_runner")

MODULE_NAME = "10_final_assembly"
DISPLAY_NAME = "最终成片包装层"
DESCRIPTION = "读取 09_video 与 08_audio 的产物，导出最终成片 final.mp4。"
KEY_OUTPUT = "final_manifest.json"
SCHEMA_VERSION = "1.1"


def _runtime_run_dir() -> Path | None:
    run_dir = os.getenv("AI_DRAMA_RUN_DIR")
    return Path(run_dir) if run_dir else None


def _resolve_upstream_file(upstream_module: str, filename: str, required: bool = True) -> Path | None:
    input_path = base_module.module_input_path(MODULE_NAME, filename)
    if input_path.exists():
        return input_path
    run_dir = _runtime_run_dir()
    if run_dir:
        fallback = run_dir / upstream_module / filename
        if fallback.exists():
            return fallback
    if required:
        raise RuntimeError(f"{MODULE_NAME} requires upstream {upstream_module}/{filename}.")
    return None


def _resolve_upstream_dir(upstream_module: str) -> Path:
    run_dir = _runtime_run_dir()
    if run_dir:
        return run_dir / upstream_module
    # Standalone fallback: use sibling module output dir, then conventional input.
    sibling_output = ROOT_DIR / upstream_module / "output"
    if sibling_output.exists():
        return sibling_output
    return base_module.module_input_path(MODULE_NAME, upstream_module)


def _read_json(path: Path) -> dict[str, Any]:
    data = io_utils.read_json(path, default=None)
    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"Invalid json input: {path}")
    return data


def _register_if_exists(artifact_name: str, path_value: Any, artifact_type: str, description: str, key: bool = False) -> None:
    if not isinstance(path_value, str) or not path_value:
        return
    path = Path(path_value)
    if not path.exists():
        return
    base_module.register_output_artifact(
        module_name=MODULE_NAME,
        artifact_name=artifact_name,
        path=path,
        artifact_type=artifact_type,
        description=description,
        metadata={"schema_version": SCHEMA_VERSION},
        is_key_output=key,
    )


def main() -> int:
    # 10 does not need LLM/Image/Audio/Video model memory. Keep it lightweight.
    resource_manager.release_image_resources()
    resource_manager.release_audio_resources()
    resource_manager.release_video_resources()
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        video_manifest_path = _resolve_upstream_file("09_video", "video_manifest.json", required=True)
        final_audio_path = _resolve_upstream_file("08_audio", "final_audio.wav", required=True)
        video_manifest = _read_json(video_manifest_path)
        video_dir = video_manifest_path.parent
        audio_dir = final_audio_path.parent
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        paths = {
            "video_manifest_path": video_manifest_path,
            "final_audio_path": final_audio_path,
            "video_dir": video_dir,
            "audio_dir": audio_dir,
        }

        stage_result = stage_runner.run_final_assembly_stages(video_manifest, paths, output_dir)
        data = stage_runner.merge_stage_outputs(video_manifest, paths, config, stage_result, output_dir)

        final_manifest_path = base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="10 关键输出：最终成片路径、音频/字幕/视频来源、导出状态、schema 校验与阶段评分。",
        )
        final_meta = {
            "module": MODULE_NAME,
            "schema_version": SCHEMA_VERSION,
            "status": data.get("status"),
            "final_video_path": data.get("final_video_path"),
            "final_manifest_path": str(final_manifest_path),
            "video_source_mode": (data.get("source") or {}).get("video_source_mode"),
            "burn_subtitles": (data.get("subtitle_policy") or {}).get("burn_subtitles"),
            "stage_status": data.get("stage_status", []),
            "quality_report": data.get("quality_report", {}),
            "schema_validation": data.get("schema_validation", {}),
        }
        final_meta_path = base_module.write_json_key_output(
            MODULE_NAME,
            "final_meta.json",
            final_meta,
            description="10 元信息：最终导出状态、来源模式、字幕策略、评分与 schema 校验。",
        )
        _register_if_exists("final.mp4", data.get("final_video_path"), "video", "10 最终成片。", key=True)
        _register_if_exists("final_manifest.json", str(final_manifest_path), "json", "10 最终 manifest。", key=True)
        _register_if_exists("final_meta.json", str(final_meta_path), "json", "10 最终 meta。", key=True)
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
