from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

base_module = import_module("00_common.base_module")
io_utils = import_module("00_common.io_utils")
resource_manager = import_module("00_common.resource_manager")

MODULE_NAME = "01_novel_parser"
DISPLAY_NAME = "小说解析系统"
DESCRIPTION = "负责通读小说、理解故事核心，并解析章节、剧情主线、冲突点、人物、场景、道具等基础信息。"
KEY_OUTPUT = "novel_analysis.json"


def read_novel_text() -> str:
    """Read optional novel input text for scaffold runs.

    Formal input convention:
    - workspace/.../input/novel.txt
    Standalone debug convention:
    - 01_novel_parser/input/novel.txt
    """
    novel_path = base_module.module_input_path(MODULE_NAME, "novel.txt")
    return io_utils.read_text(novel_path, default="").strip()


def build_story_understanding(novel_text: str) -> dict:
    """Build scaffold-level global story understanding.

    Real implementation will use local LLM to read the full user input first,
    then produce a global comprehension map before extracting events/assets.
    """
    has_input = bool(novel_text)
    return {
        "status": "scaffold",
        "requires_full_reading": True,
        "purpose": "先通读用户输入内容，理解这篇到底讲什么，再进行切段、事件、角色、场景、道具提取。",
        "one_sentence_summary": "待真实解析：一句话说明整篇内容到底讲的是什么。" if has_input else "占位：当前未提供 novel.txt。",
        "full_story_summary": "待真实解析：用较完整但不改写的方式概括全文主线。" if has_input else "占位：等待输入小说文本。",
        "core_premise": "待真实解析：故事成立的核心前提。",
        "protagonist_journey": {
            "protagonist": "待识别",
            "start_state": "待真实解析：主角开局处境、身份、误解或欲望。",
            "pressure": "待真实解析：主角遭遇的主要压迫或困境。",
            "turning_point": "待真实解析：主角认知或命运发生变化的关键点。",
            "end_state": "待真实解析：本章或本文末尾主角处境变化。",
        },
        "central_conflict": "待真实解析：全文最核心的矛盾，不是局部打斗或争吵。",
        "deep_theme": "待真实解析：故事真正想表达的底层主题。",
        "world_rules": [
            "待真实解析：故事世界里必须遵守的规则、权力关系、时代限制、职业规则等。"
        ],
        "relationship_core": [
            {
                "from": "待识别角色A",
                "to": "待识别角色B",
                "relationship": "待真实解析：二者真实关系，不只看称呼。",
                "dramatic_function": "待真实解析：这组关系在故事里的作用。",
            }
        ],
        "must_not_misread": [
            "不得只抓局部爆点而误判全文主旨。",
            "不得把铺垫人物误当主角。",
            "不得把阶段性冲突误当最终矛盾。",
            "不得把反派、导师、旁观者的功能关系读反。",
            "不得忽略第二人称、倒叙、回忆、插叙造成的理解风险。",
        ],
        "adaptation_guardrails": [
            "02 剧本改编必须服从 story_understanding，不得为了刺激随意改偏主线。",
            "后续角色、场景、分镜只可在此理解基础上细化，不可重造故事。",
        ],
    }


def build_scaffold_analysis(config: dict) -> dict:
    novel_text = read_novel_text()
    source_status = "input_found" if novel_text else "placeholder_input"
    preview = novel_text[:200]

    return {
        "schema_version": "1.0",
        "module": MODULE_NAME,
        "status": "scaffold",
        "source_status": source_status,
        "input_convention": "input/novel.txt",
        "novel": {
            "title": "未命名小说",
            "raw_text_preview": preview,
            "raw_text_length": len(novel_text),
        },
        "story_understanding": build_story_understanding(novel_text),
        "chapters": [
            {
                "chapter_id": "chapter_001",
                "title": "占位章节",
                "summary": "小说解析系统框架输出。后续将在通读全文后，接入章节切分、事件提取、冲突点提取。",
                "paragraph_count": 0,
            }
        ],
        "paragraphs": [],
        "events": [
            {
                "event_id": "event_001",
                "chapter_id": "chapter_001",
                "summary": "占位事件，用于打通 01→10 框架流程。真实事件必须服从 story_understanding。",
                "conflict_level": "placeholder",
            }
        ],
        "conflicts": [],
        "high_retention_segments": [],
        "candidate_characters": [],
        "candidate_scenes": [],
        "candidate_props": [],
        "timeline": [],
        "emotion_curve": [],
        "adaptation_hints": {
            "global_rule": "所有改编建议必须基于 story_understanding，不得只根据单个爆点片段误读全文。"
        },
        "quality_report": {
            "input_text_length": len(novel_text),
            "has_full_story_understanding": True,
            "needs_human_review": source_status == "placeholder_input",
            "parse_confidence": 0.0 if source_status == "placeholder_input" else 0.1,
        },
        "warnings": [
            "当前为 scaffold 输出，story_understanding 尚未调用真实 LLM。",
        ],
        "notes": [
            "01 必须先通读全文，理解故事核心，再提取结构信息。",
            "01 只提出角色、场景、道具候选，不直接写入 shared_assets。",
            "真实解析逻辑后续逐步接入。",
        ],
        "config": config,
    }


def main() -> int:
    try:
        config = base_module.bootstrap_module(MODULE_NAME, DISPLAY_NAME, DESCRIPTION)
        data = build_scaffold_analysis(config)
        base_module.write_json_key_output(
            MODULE_NAME,
            KEY_OUTPUT,
            data,
            description="小说解析关键输出：全局故事理解、章节、事件、候选角色、候选场景、候选道具。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"小说解析系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
