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
DESCRIPTION = "负责通读小说、理解故事核心，并解析章节、事件图谱、冲突点、全部被提及的人物/地点/物件候选、音频/视频生产预判等基础信息。"
KEY_OUTPUT = "novel_analysis.json"
SCHEMA_VERSION = "1.1"


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
    has_input = bool(novel_text)
    return {
        "status": "scaffold",
        "requires_full_reading": True,
        "purpose": "先通读用户输入内容，理解这篇到底讲什么，再进行切段、事件、角色、场景、道具、音频/视频生产预判。",
        "one_sentence_summary": "待真实解析：一句话说明整篇内容到底讲的是什么。" if has_input else "占位：当前未提供 novel.txt。",
        "full_story_summary": "待真实解析：用较完整但不改写的方式概括全文主线。" if has_input else "占位：等待输入小说文本。",
        "core_premise": "待真实解析：故事成立的核心前提。",
        "protagonist_journey": {
            "protagonist": "待识别",
            "goal": "待真实解析：主角想要什么。",
            "misbelief": "待真实解析：主角开局的误解、执念或盲区。",
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


def build_candidate_extraction_policy() -> dict:
    return {
        "mode": "extract_every_mentioned_candidate",
        "principle": "只要文章里提到过的人、地点、物件，都必须提取出来作为候选。01 不用重要性筛掉候选，重要性只作为评分字段。",
        "high_recall_rule": "候选角色、场景、道具提取宁可多，不可漏。01 不负责最终去重和压缩，03/04/05 负责合并、去重、标准化。",
        "why": "后续角色库、场景库、道具库可以合并多余候选，但无法恢复 01 阶段漏掉的人物、地点、物件。",
        "importance_rule": "importance 只能表示后续优先级，不能作为是否提取的门槛。importance=0 或 confidence 很低的对象，只要原文提到，也要作为候选输出。",
        "character_policy": {
            "extract_all_mentions": True,
            "include_minor_roles": True,
            "include_unnamed_roles": True,
            "include_group_roles": True,
            "include_title_only_roles": True,
            "include_background_roles": True,
            "examples": ["主角", "有名角色", "只出现一次的人", "称谓角色", "路人", "地痞", "衙役们", "围观百姓", "丫鬟", "老仆", "某个孩子"],
            "do_not_merge_in_01": "01 可给 possible_same_as / merge_hint，但不得直接把候选删掉。",
        },
        "scene_policy": {
            "extract_all_locations": True,
            "include_implied_scenes": True,
            "include_transition_locations": True,
            "include_mentioned_but_not_entered_locations": True,
            "examples": ["街道", "衙门", "房间", "院子", "牢房", "门口", "回忆中的地点", "只出现一句的地点", "被提到但未真正进入的地点"],
            "do_not_merge_in_01": "01 可给 possible_same_as / continuity_note，但不得直接删除相近场景候选。",
        },
        "prop_policy": {
            "extract_all_visual_objects": True,
            "include_minor_props": True,
            "include_clothing_and_symbols": True,
            "include_documents_and_money": True,
            "include_food_furniture_lamps_tools": True,
            "include_mentioned_but_not_used_objects": True,
            "examples": ["武器", "令牌", "信件", "钱袋", "衣服", "案卷", "惊堂木", "摊位", "碎饼", "灯笼", "桌椅", "茶杯", "包袱", "门", "窗"],
            "do_not_filter_in_01": "只要文章提到，就先提取；是否重要、是否入库、是否出图，交给 05 和后续模块判断。",
        },
        "candidate_confidence_rule": "不确定也要输出，但 confidence 可低，并在 risk_notes 写明不确定原因。",
        "downstream_rule": "03/04/05 必须基于这些全量候选进行合并、去重、筛选，不得要求 01 只输出少量精简候选。",
    }


def build_misread_prevention() -> dict:
    return {
        "do_not_change": [
            "不得改变原文核心设定、主角身份、核心关系、核心因果。",
            "不得把 01 的解析结果改写成剧本。",
        ],
        "do_not_misread_characters": [
            "不要把铺垫角色误判为主角。",
            "不要把同一角色按年龄、称呼、身份前缀拆成多人。",
            "遇到第二人称“你”时，必须根据上下文证据判断性别；证据不足则标记风险。",
        ],
        "do_not_misread_relationships": [
            "不要只按称呼判断关系，要根据行为、权力、利益、情绪判断真实关系。",
            "导师、压迫者、盟友、反派、旁观者的戏剧功能必须分清。",
        ],
        "do_not_misread_timeline": [
            "倒叙、回忆、插叙必须标记，不得当作当前时间线。",
            "同一事件链内的场景、人物状态、情绪推进必须连续。",
        ],
        "do_not_over_amplify": [
            "高刺激片段只可标记，不得为了爽点改变故事主线。",
            "局部冲突不能替代全文核心矛盾。",
        ],
    }


def build_event_graph() -> dict:
    return {
        "events": [
            {
                "event_id": "event_001",
                "chapter_id": "chapter_001",
                "paragraph_ids": [],
                "summary": "占位事件，用于打通 01→10 框架流程。真实事件必须服从 story_understanding。",
                "raw_text_span": "",
                "cause": "待真实解析：事件发生原因。",
                "effect": "待真实解析：事件导致的结果。",
                "before_state": "待真实解析：事件前人物/局势状态。",
                "after_state": "待真实解析：事件后人物/局势状态。",
                "characters": [],
                "scene": "",
                "props": [],
                "conflict_type": "placeholder",
                "conflict_level": 0,
                "visual_level": 0,
                "dialogue_level": 0,
                "emotion_shift": "待真实解析：事件前后情绪变化。",
                "adaptation_value": 0,
                "must_keep": False,
            }
        ],
        "event_edges": [
            {
                "from_event": "event_001",
                "to_event": None,
                "relation": "placeholder",
                "reason": "真实解析时记录事件之间的因果、推进、反转、铺垫、回忆或插叙关系。",
            }
        ],
        "main_event_path": ["event_001"],
        "side_event_paths": [],
    }


def build_candidate_characters() -> list[dict]:
    return [
        {
            "candidate_id": "char_candidate_001",
            "name": "待识别角色候选",
            "aliases": [],
            "candidate_type": "placeholder",
            "mention_type": "explicit_or_implicit",
            "first_appearance_paragraph": None,
            "appearance_paragraphs": [],
            "role_hint": "待真实解析：主角 / 配角 / 反派 / 导师 / 路人 / 群体角色。",
            "gender_hint": "unknown",
            "age_hint": "unknown",
            "identity_hint": "待真实解析：身份、职业、阵营、地位。",
            "personality_hint": "待真实解析：性格或行为倾向。",
            "relationship_to_protagonist": "unknown",
            "importance": 0,
            "confidence": 0.0,
            "visual_clues_from_text": [],
            "voice_clues_from_text": [],
            "raw_mentions": [],
            "possible_same_as": [],
            "merge_hint": "01 不直接合并删除候选，只给 03 角色库提供合并线索。",
            "risk_notes": ["真实解析时采用全量提取策略：只要文章里提到的人，都必须作为角色候选输出。"],
        }
    ]


def build_candidate_scenes() -> list[dict]:
    return [
        {
            "candidate_id": "scene_candidate_001",
            "name": "待识别场景候选",
            "aliases": [],
            "candidate_type": "placeholder",
            "mention_type": "explicit_or_implicit",
            "first_appearance_paragraph": None,
            "appearance_paragraphs": [],
            "scene_type": "待真实解析：街道 / 衙门 / 室内 / 庭院 / 山林 / 战场 / 过渡地点。",
            "time_hint": "unknown",
            "era_hint": "unknown",
            "weather_hint": "unknown",
            "visual_clues_from_text": [],
            "mood": "unknown",
            "importance": 0,
            "reuse_potential": 0,
            "confidence": 0.0,
            "possible_same_as": [],
            "continuity_note": "01 不直接合并删除场景候选，只给 04 场景库提供合并与连续性线索。",
            "risk_notes": ["真实解析时采用全量提取策略：只要文章里提到的地点，都必须作为场景候选输出。"],
        }
    ]


def build_candidate_props() -> list[dict]:
    return [
        {
            "candidate_id": "prop_candidate_001",
            "name": "待识别道具候选",
            "aliases": [],
            "candidate_type": "placeholder",
            "mention_type": "explicit_or_implicit",
            "first_appearance_paragraph": None,
            "appearance_paragraphs": [],
            "prop_type": "待真实解析：武器 / 文件 / 钱财 / 衣物 / 身份标志 / 家具 / 摊位 / 食物 / 灯具等。",
            "visual_clues_from_text": [],
            "story_function": "待真实解析：身份说明 / 冲突触发 / 动作承载 / 氛围营造 / 伏笔。",
            "importance": 0,
            "reuse_potential": 0,
            "confidence": 0.0,
            "possible_same_as": [],
            "risk_notes": ["真实解析时采用全量提取策略：只要文章里提到的物件，都必须作为道具候选输出。"],
        }
    ]


def build_voice_line_candidates() -> list[dict]:
    return [
        {
            "line_candidate_id": "vlc_001",
            "source_paragraph_ids": [],
            "source_event_id": "event_001",
            "line_type": "N",
            "speaker_hint": "旁白",
            "raw_text": "占位 voice_line 候选。真实解析时从原文中判断旁白、对白、心理 OS、留白。",
            "estimated_chars": 0,
            "estimated_duration_sec": 0.0,
            "emotion_hint": "neutral",
            "speed_hint": "normal",
            "needs_split": False,
            "split_reason": "",
            "production_note": "01 不写剧本，只预判哪些原文信息适合转成 voice_line。",
        }
    ]


def build_video_unit_candidates() -> list[dict]:
    return [
        {
            "unit_candidate_id": "vuc_001",
            "event_id": "event_001",
            "voice_line_candidate_ids": ["vlc_001"],
            "main_scene": "待识别场景",
            "main_characters": [],
            "main_action_chain": [
                "待真实解析：一个视频单元内的连续动作链，建议不超过 3 个动作阶段。"
            ],
            "estimated_duration_sec": 0.0,
            "target_duration_range_sec": [6, 12],
            "single_scene_required": True,
            "action_chain_count": 0,
            "needs_split": False,
            "split_warning": "",
            "production_note": "01 只预判 6-12 秒视频单元可行性，不生成视频 JSON。",
        }
    ]


def build_asset_binding_hints() -> list[dict]:
    return [
        {
            "event_id": "event_001",
            "scene_candidate_id": None,
            "character_candidate_ids": [],
            "prop_candidate_ids": [],
            "layout_need": "待真实解析：单人特写 / 双人对峙 / 群像 / 室内审案 / 动作过场等。",
            "continuity_risk": "待真实解析：同一事件内是否需要固定场景、固定站位、固定道具。",
            "visual_priority": "待真实解析：角色表情 / 道具 / 场景压迫感 / 动作 / 光线氛围。",
        }
    ]


def build_visual_risk_report() -> dict:
    return {
        "gender_ambiguity": [],
        "age_ambiguity": [],
        "identity_ambiguity": [],
        "modern_object_risk": [],
        "scene_continuity_risk": [],
        "too_many_characters_events": [],
        "unclear_actor_count_events": [],
        "prop_confusion_risk": [],
        "candidate_over_extraction_note": "角色/场景/道具候选多不是问题，遗漏才是问题。只要文章提到过，就应进入候选。后续 03/04/05 负责筛选合并。",
        "style_risk": [
            "真实解析时必须识别现代物品、现代服饰、错误时代、欧美脸、卡通/3D 风格等风险。"
        ],
    }


def build_chapter_memory_update() -> dict:
    return {
        "new_facts": [],
        "changed_relationships": [],
        "new_unresolved_clues": [],
        "resolved_clues": [],
        "timeline_updates": [],
        "character_state_updates": [],
        "write_policy": "01 只提出全书记忆更新建议，不直接写入 global_memory。",
    }


def build_scaffold_analysis(config: dict) -> dict:
    novel_text = read_novel_text()
    source_status = "input_found" if novel_text else "placeholder_input"
    preview = novel_text[:200]
    event_graph = build_event_graph()
    candidate_characters = build_candidate_characters()
    candidate_scenes = build_candidate_scenes()
    candidate_props = build_candidate_props()

    return {
        "schema_version": SCHEMA_VERSION,
        "module": MODULE_NAME,
        "status": "scaffold",
        "source_status": source_status,
        "input": {
            "input_convention": "input/novel.txt",
            "source_file": "input/novel.txt",
            "raw_text_length": len(novel_text),
            "raw_text_preview": preview,
        },
        "novel": {
            "title": "未命名小说",
            "language": "zh-CN",
            "genre_guess": "待真实解析",
            "narrative_pov": "待真实解析",
            "main_tense": "待真实解析",
            "raw_text_preview": preview,
            "raw_text_length": len(novel_text),
        },
        "story_understanding": build_story_understanding(novel_text),
        "misread_prevention": build_misread_prevention(),
        "candidate_extraction_policy": build_candidate_extraction_policy(),
        "chapters": [
            {
                "chapter_id": "chapter_001",
                "title": "占位章节",
                "summary": "小说解析系统框架输出。后续将在通读全文后，接入章节切分、事件图谱、冲突点提取。",
                "paragraph_count": 0,
                "core_conflict": "待真实解析",
                "ending_hook": "待真实解析",
            }
        ],
        "paragraphs": [],
        "event_graph": event_graph,
        "events": event_graph["events"],
        "conflicts": [],
        "high_retention_segments": [],
        "candidate_characters": candidate_characters,
        "candidate_scenes": candidate_scenes,
        "candidate_props": candidate_props,
        "voice_line_candidates": build_voice_line_candidates(),
        "video_unit_candidates": build_video_unit_candidates(),
        "asset_binding_hints": build_asset_binding_hints(),
        "timeline": [],
        "emotion_curve": [],
        "visual_risk_report": build_visual_risk_report(),
        "evidence_index": [
            {
                "evidence_id": "evd_001",
                "paragraph_id": None,
                "raw_text": "",
                "supports": [
                    "story_understanding",
                    "event_graph.events.event_001",
                    "candidate_extraction_policy",
                ],
                "note": "真实解析时，每个关键判断都应尽量回链到原文证据。候选资产提取也要保留 raw_mentions / appearance_paragraphs。",
            }
        ],
        "adaptation_hints": {
            "global_rule": "所有改编建议必须基于 story_understanding，不得只根据单个爆点片段误读全文。",
            "must_keep_events": [],
            "can_compress_events": [],
            "can_skip_events": [],
            "best_opening_candidates": [],
            "best_cliffhanger_candidates": [],
            "risk_notes": [],
        },
        "chapter_memory_update": build_chapter_memory_update(),
        "quality_report": {
            "input_text_length": len(novel_text),
            "paragraph_count": 0,
            "event_count": len(event_graph["events"]),
            "character_candidate_count": len(candidate_characters),
            "scene_candidate_count": len(candidate_scenes),
            "prop_candidate_count": len(candidate_props),
            "has_full_story_understanding": True,
            "has_event_graph": True,
            "has_voice_line_candidates": True,
            "has_video_unit_candidates": True,
            "has_visual_risk_report": True,
            "has_evidence_index": True,
            "candidate_extraction_mode": "extract_every_mentioned_candidate",
            "asset_candidate_review_policy": "候选过多不算错误；只要文章提到过的人、地点、物件没有进入候选，就需要返工。",
            "story_understanding_score": 0.0 if source_status == "placeholder_input" else 0.1,
            "event_graph_score": 0.0 if source_status == "placeholder_input" else 0.1,
            "visual_readiness_score": 0.0,
            "audio_readiness_score": 0.0,
            "needs_retry": False,
            "retry_reason": "",
            "needs_human_review": source_status == "placeholder_input",
            "parse_confidence": 0.0 if source_status == "placeholder_input" else 0.1,
        },
        "warnings": [
            "当前为 scaffold 输出，story_understanding / event_graph / voice_line_candidates 尚未调用真实 LLM。",
            "当前 voice_line 和 video_unit 仅为生产预判结构，不代表最终剧本或视频 JSON。",
            "当前候选角色/场景/道具为占位样例；真实解析时必须提取文章里提到过的全部人、地点、物件。",
        ],
        "notes": [
            "01 必须先通读全文，理解故事核心，再提取结构信息。",
            "01 只提出角色、场景、道具候选，不直接写入 shared_assets。",
            "01 的候选提取策略是全量提取：只要文章里提到过的人、地点、物件，都必须作为候选。",
            "重要性只影响后续优先级，不影响是否提取。",
            "01 可以给改编建议和生产预判，但不能直接写剧本、分镜、图片提示词或视频提示词。",
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
            description="小说解析关键输出：全局故事理解、事件图谱、生产预判、全量候选资产与原文证据链。",
        )
        base_module.write_placeholder_output(MODULE_NAME, {
            "module": MODULE_NAME,
            "status": "scaffold",
            "message": f"小说解析系统框架已运行，关键输出已生成：{KEY_OUTPUT}",
            "key_output": KEY_OUTPUT,
            "schema_version": SCHEMA_VERSION,
            "config": config,
        })
        print(f"{DISPLAY_NAME} finished. key output: {KEY_OUTPUT}")
        return 0
    finally:
        resource_manager.release_local_resources(MODULE_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
