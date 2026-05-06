from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "08_audio"
DISPLAY_NAME = "音频系统"
DESCRIPTION = "负责根据对白、OS、留白、情绪、音色配置生成完整音频。"
KEY_OUTPUT = "final_audio.wav"


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        audio_path = base_module.write_text_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            "PLACEHOLDER AUDIO FILE. Real TTS output will replace this file.",
            description="音频关键输出：完整音频文件。当前为框架占位文件。",
            artifact_type="audio",
            metadata={
                "placeholder": True,
                "required_upstream": "02_script_writer.script.json",
                "future_engine": "CosyVoice2 / other local TTS",
            },
        )
        audio_manifest = {
            "module": MODULE_NAME,
            "status": "scaffold",
            "audio": {
                "path": str(audio_path),
                "type": "placeholder_wav",
                "duration_seconds": 0,
                "status": "placeholder",
            },
            "source": {
                "required_upstream": "02_script_writer.script.json",
                "note": "当前为框架占位输出，后续接入对白、OS、留白、情绪、音色生成逻辑。",
            },
            "config": config,
        }
        base_module.write_json_key_output(
            MODULE_NAME,
            "audio_manifest.json",
            audio_manifest,
            description="音频清单：记录音频路径、时长、音色与生成状态。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"音频系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
