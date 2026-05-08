from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from importlib import import_module
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "00_style_system"
DISPLAY_NAME = "风格圣经系统"
DESCRIPTION = "生成全流程统一风格圣经、图片风格锁、视频风格锁和负向风格禁区。"
SCHEMA_VERSION = "1.0"


def _load_presets() -> dict[str, Any]:
    path = ROOT_DIR / MODULE_NAME / "presets" / "style_presets.json"
    data = io_utils.read_json(path, default={})
    return data if isinstance(data, dict) else {}


def _select_preset(presets_data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    presets = presets_data.get("presets", {})
    if not isinstance(presets, dict) or not presets:
        raise ValueError("style presets not found")

    requested = os.getenv("AI_DRAMA_STYLE_PRESET") or presets_data.get("default_preset") or "ancient_live_action_realistic"
    if requested not in presets:
        available = ", ".join(sorted(presets.keys()))
        print(f"[STYLE] Unknown preset {requested!r}; fallback to default. Available: {available}")
        requested = presets_data.get("default_preset") or next(iter(presets.keys()))

    preset = presets.get(requested, {})
    if not isinstance(preset, dict):
        raise ValueError(f"invalid style preset: {requested}")
    return requested, preset


def _lines(title: str, values: list[Any]) -> str:
    clean = [str(v).strip() for v in values if str(v).strip()]
    if not clean:
        return f"## {title}\n\n- 无\n"
    return f"## {title}\n\n" + "\n".join(f"- {item}" for item in clean) + "\n"


def _build_style_bible(style_id: str, preset: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    intensity = os.getenv("AI_DRAMA_STYLE_INTENSITY", "strong")
    return {
        "schema_version": SCHEMA_VERSION,
        "module": MODULE_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "style_id": style_id,
        "display_name": preset.get("display_name", style_id),
        "style_intensity": intensity,
        "visual_type": preset.get("visual_type", ""),
        "era": preset.get("era", ""),
        "core_style": preset.get("core_style", ""),
        "story_tone": preset.get("story_tone", ""),
        "camera_language": preset.get("camera_language", []),
        "lighting": preset.get("lighting", []),
        "color_palette": preset.get("color_palette", []),
        "costume_rules": preset.get("costume_rules", []),
        "scene_rules": preset.get("scene_rules", []),
        "positive_keywords": preset.get("positive_keywords", []),
        "negative_keywords": preset.get("negative_keywords", []),
        "global_rules": [
            "所有文本、资产、分镜、图片提示词和视频提示词必须继承本风格圣经。",
            "后续模块不得自行切换时代、画风、材质、光影、服装体系或镜头语言。",
            "小说原文未明确要求特殊风格时，默认以本风格为最高约束。",
            "若剧情需要临时差异，只允许在本风格体系内变化，不允许跨风格污染。",
            "图片生成阶段优先使用 image_style_lock.txt，视频生成阶段优先使用 video_style_lock.txt。"
        ],
        "output_files": [
            "style_bible.json",
            "style_bible.md",
            "style_prompt_prefix.txt",
            "image_style_lock.txt",
            "video_style_lock.txt",
            "style_negative_prompt.txt",
            "style_meta.json"
        ],
        "runtime": config.get("runtime", {})
    }


def _build_markdown(bible: dict[str, Any]) -> str:
    parts = [
        "# Style Bible / 风格圣经\n",
        f"风格ID：`{bible.get('style_id')}`\n",
        f"显示名称：{bible.get('display_name')}\n",
        f"视觉类型：{bible.get('visual_type')}\n",
        f"时代体系：{bible.get('era')}\n",
        "## 核心风格\n\n" + str(bible.get("core_style", "")) + "\n",
        "## 叙事气质\n\n" + str(bible.get("story_tone", "")) + "\n",
        _lines("镜头语言", bible.get("camera_language", [])),
        _lines("光影", bible.get("lighting", [])),
        _lines("色彩", bible.get("color_palette", [])),
        _lines("服装规则", bible.get("costume_rules", [])),
        _lines("场景规则", bible.get("scene_rules", [])),
        _lines("正向关键词", bible.get("positive_keywords", [])),
        _lines("负向关键词", bible.get("negative_keywords", [])),
        _lines("全局继承规则", bible.get("global_rules", [])),
    ]
    return "\n".join(parts).strip() + "\n"


def _build_prompt_prefix(bible: dict[str, Any]) -> str:
    return "\n".join([
        "【最高风格规则】",
        f"当前项目风格：{bible.get('display_name')}（{bible.get('style_id')}）。",
        f"核心风格：{bible.get('core_style')}",
        f"叙事气质：{bible.get('story_tone')}",
        "所有输出必须继承本风格圣经；不得自行切换时代、画风、材质、光影、服装体系或镜头语言。",
        "若原文没有明确指定特殊风格，默认保持当前项目风格。",
    ]).strip() + "\n"


def _build_image_lock(bible: dict[str, Any]) -> str:
    positives = ", ".join(str(v) for v in bible.get("positive_keywords", []))
    camera = "，".join(str(v) for v in bible.get("camera_language", []))
    light = "，".join(str(v) for v in bible.get("lighting", []))
    color = "，".join(str(v) for v in bible.get("color_palette", []))
    costume = "，".join(str(v) for v in bible.get("costume_rules", []))
    scene = "，".join(str(v) for v in bible.get("scene_rules", []))
    return "\n".join([
        f"{bible.get('core_style')}",
        f"视觉类型：{bible.get('visual_type')}；时代体系：{bible.get('era')}。",
        f"镜头：{camera}。",
        f"光影：{light}。",
        f"色彩：{color}。",
        f"服装：{costume}。",
        f"场景：{scene}。",
        f"positive keywords: {positives}",
        "同一项目内所有图片必须像同一套视觉系统、同一部作品、同一摄影/美术体系。",
    ]).strip() + "\n"


def _build_video_lock(bible: dict[str, Any]) -> str:
    positives = ", ".join(str(v) for v in bible.get("positive_keywords", [])[:5])
    negatives = ", ".join(str(v) for v in bible.get("negative_keywords", [])[:8])
    return " ".join([
        str(bible.get("visual_type", "")),
        positives,
        "same character, same costume, same scene, consistent lighting, realistic and stable motion, subtle camera movement.",
        f"avoid: {negatives}."
    ]).strip() + "\n"


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        presets_data = _load_presets()
        style_id, preset = _select_preset(presets_data)
        bible = _build_style_bible(style_id, preset, config)

        markdown = _build_markdown(bible)
        prompt_prefix = _build_prompt_prefix(bible)
        image_lock = _build_image_lock(bible)
        video_lock = _build_video_lock(bible)
        negative_prompt = ", ".join(str(v) for v in bible.get("negative_keywords", [])) + "\n"

        base_module.write_json_key_output(MODULE_NAME, "style_bible.json", bible, "全流程风格圣经 JSON。")
        base_module.write_text_key_output(MODULE_NAME, "style_bible.md", markdown, "全流程风格圣经 Markdown。", "markdown")
        base_module.write_text_key_output(MODULE_NAME, "style_prompt_prefix.txt", prompt_prefix, "文本 LLM 阶段统一风格前缀。", "text")
        base_module.write_text_key_output(MODULE_NAME, "image_style_lock.txt", image_lock, "图片生成阶段统一风格锁。", "text")
        base_module.write_text_key_output(MODULE_NAME, "video_style_lock.txt", video_lock, "视频生成阶段统一风格锁。", "text")
        base_module.write_text_key_output(MODULE_NAME, "style_negative_prompt.txt", negative_prompt, "统一负向风格词。", "text")
        base_module.write_json_key_output(MODULE_NAME, "style_meta.json", {
            "module": MODULE_NAME,
            "schema_version": SCHEMA_VERSION,
            "style_id": style_id,
            "display_name": bible.get("display_name"),
            "available_presets": sorted((presets_data.get("presets") or {}).keys()),
            "env_override": "AI_DRAMA_STYLE_PRESET",
            "status": "success"
        }, "风格系统元信息。")

        print(f"{DISPLAY_NAME} finished. style preset: {style_id}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
