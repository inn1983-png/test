from __future__ import annotations

import json
import struct
import wave
from pathlib import Path


def build_minimal_project(run_dir: str | Path) -> dict[str, str]:
    run_dir = Path(run_dir)
    created: dict[str, str] = {}

    def _write_json(rel: str, data: dict) -> None:
        path = run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        created[rel] = str(path)

    def _write_wav(rel: str, duration_sec: float = 0.1, sample_rate: int = 22050) -> None:
        path = run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        n_frames = int(sample_rate * duration_sec)
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))
        created[rel] = str(path)

    novel_analysis = {
        "schema_version": "1.0",
        "module": "01_novel_parser",
        "status": "success",
        "characters": [
            {"name": "李云飞", "role": "男主", "description": "江湖侠客，剑术超群"},
            {"name": "苏婉儿", "role": "女配", "description": "丞相之女，聪慧过人"},
        ],
        "scenes": [
            {"name": "竹林小径", "description": "幽静竹林，晨雾缭绕"},
        ],
        "props": [
            {"name": "碧血剑", "description": "传世宝剑，剑身泛着幽蓝光芒"},
        ],
        "key_dialogues": [
            {"character": "李云飞", "line": "此剑名为碧血，愿为天下苍生而鸣！"},
        ],
        "narration_segments": [
            {"text": "晨光初照，竹林深处传来阵阵剑鸣。"},
        ],
    }
    _write_json("01_novel_parser/novel_analysis.json", novel_analysis)

    script = {
        "schema_version": "1.0",
        "module": "02_script_writer",
        "status": "success",
        "scenes": [
            {
                "scene_id": "S01",
                "scene_name": "竹林小径",
                "shots": [
                    {
                        "shot_id": "S01_01",
                        "type": "旁白",
                        "content": "晨光初照，竹林深处传来阵阵剑鸣。",
                        "duration_estimate": 5.0,
                    },
                    {
                        "shot_id": "S01_02",
                        "type": "对白",
                        "character": "李云飞",
                        "content": "此剑名为碧血，愿为天下苍生而鸣！",
                        "duration_estimate": 4.0,
                    },
                ],
            },
        ],
    }
    _write_json("02_script_writer/script.json", script)

    characters = {
        "schema_version": "1.0",
        "module": "03_character_system",
        "status": "success",
        "characters": [
            {"id": "C01", "name": "李云飞", "role": "男主", "appearance": "白衣长剑，英姿飒爽"},
            {"id": "C02", "name": "苏婉儿", "role": "女配", "appearance": "素衣罗裙，温婉端庄"},
        ],
    }
    _write_json("03_character_system/characters.json", characters)

    scenes = {
        "schema_version": "1.0",
        "module": "04_scene_system",
        "status": "success",
        "scenes": [
            {"id": "SC01", "name": "竹林小径", "description": "幽静竹林，晨雾缭绕", "mood": "清冷"},
        ],
    }
    _write_json("04_scene_system/scenes.json", scenes)

    props = {
        "schema_version": "1.0",
        "module": "05_prop_system",
        "status": "success",
        "props": [
            {"id": "P01", "name": "碧血剑", "description": "传世宝剑，剑身泛着幽蓝光芒"},
        ],
    }
    _write_json("05_prop_system/props.json", props)

    storyboard = {
        "schema_version": "1.0",
        "module": "06_storyboard",
        "status": "success",
        "frames": [
            {
                "frame_id": "F01",
                "shot_id": "S01_01",
                "scene": "竹林小径",
                "characters": ["李云飞"],
                "action": "李云飞持剑而立，晨雾中身影若隐若现",
                "dialogue": None,
                "narration": "晨光初照，竹林深处传来阵阵剑鸣。",
                "duration": 5.0,
            },
            {
                "frame_id": "F02",
                "shot_id": "S01_02",
                "scene": "竹林小径",
                "characters": ["李云飞"],
                "action": "李云飞举剑向天，剑身泛着幽蓝光芒",
                "dialogue": "此剑名为碧血，愿为天下苍生而鸣！",
                "narration": None,
                "duration": 4.0,
            },
        ],
    }
    _write_json("06_storyboard/storyboard.json", storyboard)

    image_manifest = {
        "schema_version": "1.0",
        "module": "07_storyboard_image",
        "status": "success",
        "dry_run": True,
        "images": [
            {"frame_id": "F01", "image_path": "images/F01.png", "ready": False},
            {"frame_id": "F02", "image_path": "images/F02.png", "ready": False},
        ],
    }
    _write_json("07_storyboard_image/image_manifest.json", image_manifest)

    _write_wav("08_audio/final_audio.wav", duration_sec=9.0)

    audio_timeline = {
        "schema_version": "1.0",
        "module": "08_audio",
        "status": "success",
        "dry_run": True,
        "segments": [
            {"frame_id": "F01", "start": 0.0, "end": 5.0, "type": "narration"},
            {"frame_id": "F02", "start": 5.0, "end": 9.0, "type": "dialogue", "character": "李云飞"},
        ],
        "total_duration": 9.0,
    }
    _write_json("08_audio/audio_timeline.json", audio_timeline)

    srt_content = "1\n00:00:00,000 --> 00:00:05,000\n晨光初照，竹林深处传来阵阵剑鸣。\n\n2\n00:00:05,000 --> 00:00:09,000\n此剑名为碧血，愿为天下苍生而鸣！\n"
    srt_path = run_dir / "08_audio" / "subtitle.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(srt_content, encoding="utf-8")
    created["08_audio/subtitle.srt"] = str(srt_path)

    ass_content = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,晨光初照，竹林深处传来阵阵剑鸣。\nDialogue: 0,0:00:05.00,0:00:09.00,Default,,0,0,0,,此剑名为碧血，愿为天下苍生而鸣！\n"
    ass_path = run_dir / "08_audio" / "subtitle.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    created["08_audio/subtitle.ass"] = str(ass_path)

    video_manifest = {
        "schema_version": "1.0",
        "module": "09_video",
        "status": "success",
        "dry_run": True,
        "segments": [
            {"frame_id": "F01", "output_clip_path": None, "ready": False},
            {"frame_id": "F02", "output_clip_path": None, "ready": False},
        ],
    }
    _write_json("09_video/video_manifest.json", video_manifest)

    return created


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "project_validation_001"
    root = Path(__file__).resolve().parents[2]
    run_dir = root / "workspace" / "projects" / target
    result = build_minimal_project(run_dir)
    print(json.dumps({"target": str(run_dir), "created_files": len(result), "files": list(result.keys())}, ensure_ascii=False, indent=2))
