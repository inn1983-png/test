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
stage_runner = import_module("09_video.core.stage_runner")

MODULE_NAME = "09_video"
DISPLAY_NAME = "视频生成系统"
DESCRIPTION = "读取 07 分镜图片文件夹与 08 final_audio.wav，按 10/12 秒音频切片调用本地 LTX2.3 ComfyUI 工作流生成视频段，支持断点续跑与最终合并。"
KEY_OUTPUT = "video_manifest.json"
SCHEMA_VERSION = "1.0"


def _read_json_upstream(module_name: str, filename: str) -> dict[str, Any]:
    input_path = base_module.module_input_path(MODULE_NAME, filename)
    if not input_path.exists():
        run_dir = os.getenv("AI_DRAMA_RUN_DIR")
        if run_dir:
            fallback = Path(run_dir) / module_name / filename
            if fallback.exists():
                input_path = fallback
    data = io_utils.read_json(input_path, default=None)
    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"{MODULE_NAME} requires upstream {module_name}/{filename}.")
    return data


def _resolve_file_upstream(module_name: str, filename: str) -> Path:
    input_path = base_module.module_input_path(MODULE_NAME, filename)
    if input_path.exists():
        return input_path
    run_dir = os.getenv("AI_DRAMA_RUN_DIR")
    if run_dir:
        fallback = Path(run_dir) / module_name / filename
        if fallback.exists():
            return fallback
    raise RuntimeError(f"{MODULE_NAME} requires upstream {module_name}/{filename}.")


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
    try:
        resource_manager.release_image_resources()
        resource_manager.release_audio_resources()
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        image_manifest = _read_json_upstream("07_storyboard_image", "image_manifest.json")
        audio_timeline = _read_json_upstream("08_audio", "audio_timeline.json")
        final_audio_path = _resolve_file_upstream("08_audio", "final_audio.wav")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)

        stage_result = stage_runner.run_video_stages(image_manifest, audio_timeline, final_audio_path, output_dir)
        data = stage_runner.merge_stage_outputs(image_manifest, audio_timeline, final_audio_path, config, stage_result, output_dir)

        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="09 关键输出：视频分段计划、ComfyUI/LTX2.3 执行结果、断点续跑状态、合并结果与最终视频路径。",
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "video_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "execution_mode": data.get("execution_mode"),
                "segment_count": len(data.get("video_segments", []) or []),
                "completed_segment_count": len([s for s in data.get("video_segments", []) or [] if isinstance(s, dict) and s.get("status") == "success"]),
                "final_video_path": data.get("final_video_path"),
                "stage_status": data.get("stage_status", []),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
            },
            description="09 元信息：视频阶段状态、执行模式、分段完成度、合并路径、评分与 schema 校验。",
        )
        _register_if_exists("final_video.mp4", data.get("final_video_path"), "video", "09 可选关键产物：自动合并后的视频成品。", key=True)
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_video_resources()
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
