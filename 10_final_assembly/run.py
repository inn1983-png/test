from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
base_module = import_module("00_common.base_module")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "10_final_assembly"
DISPLAY_NAME = "成片拼接系统"
DESCRIPTION = "负责把视频片段、音频、字幕、封面等素材拼接为最终成片。"
KEY_OUTPUT = "final.mp4"


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        final_path = base_module.write_text_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            "PLACEHOLDER FINAL VIDEO. Real final assembly will replace this file.",
            description="成片关键输出：最终视频文件。当前为框架占位文件。",
            artifact_type="video",
            metadata={
                "placeholder": True,
                "required_upstream": "09_video.video_manifest.json",
            },
        )
        assembly_manifest = {
            "module": MODULE_NAME,
            "status": "scaffold",
            "final_video": {
                "path": str(final_path),
                "type": "placeholder_mp4",
                "duration_seconds": 0,
                "status": "placeholder",
            },
            "source": {
                "required_upstream": "09_video.video_manifest.json",
                "note": "当前为框架占位输出，后续接入视频拼接、字幕、封面、最终导出逻辑。",
            },
            "config": config,
        }
        base_module.write_json_key_output(
            MODULE_NAME,
            "assembly_manifest.json",
            assembly_manifest,
            description="成片拼接清单：记录最终视频、片段来源、字幕与封面状态。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"成片拼接系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)

if __name__ == "__main__":
    raise SystemExit(main())
