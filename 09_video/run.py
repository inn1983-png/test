from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "09_video"
DISPLAY_NAME = "视频生成系统"
DESCRIPTION = "负责读取分镜图文件夹和音频文件，调用本地视频模型生成视频片段。"
KEY_OUTPUT = "video_manifest.json"


def build_scaffold_video_manifest(config: dict) -> dict:
    clip_path = base_module.write_text_key_output(
        MODULE_NAME,
        "clip_001.mp4",
        "PLACEHOLDER VIDEO CLIP. Real video generation will replace this file.",
        description="占位视频片段文件，用于框架闭环测试。",
        artifact_type="video",
        metadata={"clip_id": "clip_001", "placeholder": True},
    )
    return {
        "module": MODULE_NAME,
        "status": "scaffold",
        "source": {
            "required_upstream": [
                "07_storyboard_image.image_manifest.json",
                "08_audio.final_audio.wav"
            ],
            "note": "当前为框架占位输出，后续接入 LTX / ComfyUI 视频生成逻辑。",
        },
        "clips": [
            {
                "clip_id": "clip_001",
                "shot_range": ["shot_001"],
                "path": str(clip_path),
                "duration_seconds": 0,
                "type": "placeholder_mp4",
                "status": "placeholder",
            }
        ],
        "generation_strategy": {
            "segment_seconds": 12,
            "image_reference_mode": "storyboard_image_folder",
            "audio_driven": True,
            "status": "placeholder",
        },
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_video_manifest(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="视频关键输出：视频片段清单、路径、时长、生成策略。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"视频生成系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
