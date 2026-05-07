from __future__ import annotations

import os
import sys
from pathlib import Path
from importlib import import_module
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")
stage_runner = import_module("08_audio.core.stage_runner")

MODULE_NAME = "08_audio"
DISPLAY_NAME = "配音生成系统"
DESCRIPTION = "负责读取 02 剧本文本，构建配音队列，调用本地 index-tts / IndexTTS2 生成分段音频，并合成为 final_audio.wav。"
KEY_OUTPUT = "final_audio.wav"
SCHEMA_VERSION = "1.0"


def _read_upstream(module_name: str, filename: str) -> dict[str, Any]:
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


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        script = _read_upstream("02_script_writer", "script.json")
        _, output_dir = base_module.get_runtime_module_dirs(MODULE_NAME)
        stage_result = stage_runner.run_audio_stages(script, output_dir)
        data = stage_runner.merge_stage_outputs(script, config, stage_result, output_dir)

        final_audio = Path(data.get("final_audio_path") or Path(output_dir) / KEY_OUTPUT)
        if not final_audio.exists():
            raise RuntimeError(f"08_audio expected final audio but file is missing: {final_audio}")

        base_module.register_output_artifact(
            module_name=MODULE_NAME,
            artifact_name=KEY_OUTPUT,
            path=final_audio,
            artifact_type="audio",
            description="08 关键输出：最终合成音频文件。",
            metadata={
                "schema_version": SCHEMA_VERSION,
                "execution_mode": data.get("execution_mode"),
                "duration_seconds": data.get("duration_seconds"),
                "segment_count": len(data.get("segments", []) or []),
            },
            is_key_output=True,
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "audio_manifest.json",
            data,
            description="08 音频清单：台词队列、分段音频、执行结果、合成信息、评分与 schema 校验。",
        )
        base_module.write_json_key_output(
            MODULE_NAME,
            "audio_meta.json",
            {
                "module": MODULE_NAME,
                "schema_version": SCHEMA_VERSION,
                "status": data.get("status"),
                "execution_mode": data.get("execution_mode"),
                "final_audio_path": str(final_audio),
                "duration_seconds": data.get("duration_seconds"),
                "stage_status": data.get("stage_status", []),
                "quality_report": data.get("quality_report", {}),
                "schema_validation": data.get("schema_validation", {}),
            },
            description="08 元信息：音频阶段状态、执行模式、时长、评分与 schema 校验。",
        )
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
