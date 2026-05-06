from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")

SCHEMA_VERSION = "1.2"

STAGES: list[dict[str, str]] = [
    {"stage_id": "01A", "name": "story_understanding", "prompt_file": "prompts/01A_story_understanding.md", "output_file": "01A_story_understanding.json"},
    {"stage_id": "01B", "name": "paragraph_split", "prompt_file": "prompts/01B_paragraph_split.md", "output_file": "01B_paragraphs.json"},
    {"stage_id": "01C", "name": "event_graph", "prompt_file": "prompts/01C_event_graph.md", "output_file": "01C_event_graph.json"},
    {"stage_id": "01D", "name": "candidate_extract", "prompt_file": "prompts/01D_candidate_extract.md", "output_file": "01D_candidates.json"},
    {"stage_id": "01E", "name": "production_predict", "prompt_file": "prompts/01E_production_predict.md", "output_file": "01E_production_predict.json"},
    {"stage_id": "01F", "name": "quality_check", "prompt_file": "prompts/01F_quality_check.md", "output_file": "01F_quality_check.json"},
]


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def build_stage_outputs(novel_text: str) -> dict[str, dict[str, Any]]:
    has_input = bool(novel_text.strip())
    source_status = "input_found" if has_input else "placeholder_input"
    return {
        "01A": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01A_story_understanding",
            "status": "scaffold",
            "story_understanding": {
                "requires_full_reading": True,
                "one_sentence_summary": "待真实解析" if has_input else "占位：当前未提供 novel.txt。",
                "full_story_summary": "待真实解析" if has_input else "占位：等待输入小说文本。",
                "core_premise": "待真实解析",
                "protagonist_journey": {},
                "central_conflict": "待真实解析",
                "deep_theme": "待真实解析",
                "world_rules": [],
                "relationship_core": [],
                "must_not_misread": [],
                "adaptation_guardrails": [],
            },
            "story_spine": {},
            "viewer_experience_plan": {},
            "information_reveal_plan": [],
            "adaptation_strategy": {},
            "misread_prevention": {},
        },
        "01B": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01B_paragraph_split",
            "status": "scaffold",
            "chapters": [{"chapter_id": "chapter_001", "title": "占位章节", "paragraph_count": 0}],
            "paragraphs": [],
            "timeline": [],
        },
        "01C": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01C_event_graph",
            "status": "scaffold",
            "event_graph": {"events": [{"event_id": "event_001", "paragraph_ids": [], "summary": "占位事件"}], "event_edges": [], "main_event_path": ["event_001"], "side_event_paths": []},
            "conflicts": [],
            "high_retention_segments": [],
            "scene_value_map": [],
            "character_arc_map": [],
        },
        "01D": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01D_candidate_extract",
            "status": "scaffold",
            "candidate_extraction_policy": {"mode": "extract_every_mentioned_candidate", "principle": "只要文章里提到过的人、地点、物件，都必须提取出来作为候选。"},
            "candidate_characters": [],
            "candidate_scenes": [],
            "candidate_props": [],
            "asset_binding_hints": [],
            "visual_risk_report": {},
        },
        "01E": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01E_production_predict",
            "status": "scaffold",
            "voice_line_candidates": [],
            "video_unit_candidates": [],
            "emotion_curve": [],
            "golden_lines": [],
            "confusion_risk_report": {},
        },
        "01F": {
            "schema_version": SCHEMA_VERSION,
            "stage": "01F_quality_check",
            "status": "scaffold",
            "evidence_index": [],
            "quality_report": {"input_text_length": len(novel_text), "source_status": source_status, "stage_mode": "scaffold", "needs_retry": False},
            "warnings": ["当前为 scaffold 输出，01A–01F 尚未调用真实 LLM。"],
            "chapter_memory_update": {},
        },
    }


def run_scaffold_stages(novel_text: str, output_dir: str | Path) -> dict[str, Any]:
    outputs = build_stage_outputs(novel_text)
    stage_status = []
    for stage in STAGES:
        output_path = _write_stage(output_dir, stage["output_file"], outputs[stage["stage_id"]])
        stage_status.append({**stage, "status": "scaffold", "output_path": output_path})
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "scaffold", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(novel_text: str, config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e, f = outputs["01A"], outputs["01B"], outputs["01C"], outputs["01D"], outputs["01E"], outputs["01F"]
    source_status = "input_found" if novel_text.strip() else "placeholder_input"
    event_graph = c["event_graph"]
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "01_novel_parser",
        "status": "scaffold",
        "source_status": source_status,
        "stage_mode": stage_result["stage_mode"],
        "stage_status": stage_result["stage_status"],
        "input": {"input_convention": "input/novel.txt", "source_file": "input/novel.txt", "raw_text_length": len(novel_text), "raw_text_preview": novel_text[:200]},
        "novel": {"title": "未命名小说", "language": "zh-CN", "genre_guess": "待真实解析", "narrative_pov": "待真实解析", "main_tense": "待真实解析"},
        "story_understanding": a["story_understanding"],
        "story_spine": a["story_spine"],
        "viewer_experience_plan": a["viewer_experience_plan"],
        "information_reveal_plan": a["information_reveal_plan"],
        "adaptation_strategy": a["adaptation_strategy"],
        "misread_prevention": a["misread_prevention"],
        "chapters": b["chapters"],
        "paragraphs": b["paragraphs"],
        "timeline": b["timeline"],
        "event_graph": event_graph,
        "events": event_graph.get("events", []),
        "conflicts": c["conflicts"],
        "high_retention_segments": c["high_retention_segments"],
        "scene_value_map": c["scene_value_map"],
        "character_arc_map": c["character_arc_map"],
        "candidate_extraction_policy": d["candidate_extraction_policy"],
        "candidate_characters": d["candidate_characters"],
        "candidate_scenes": d["candidate_scenes"],
        "candidate_props": d["candidate_props"],
        "asset_binding_hints": d["asset_binding_hints"],
        "visual_risk_report": d["visual_risk_report"],
        "voice_line_candidates": e["voice_line_candidates"],
        "video_unit_candidates": e["video_unit_candidates"],
        "emotion_curve": e["emotion_curve"],
        "golden_lines": e["golden_lines"],
        "confusion_risk_report": e["confusion_risk_report"],
        "evidence_index": f["evidence_index"],
        "quality_report": f["quality_report"],
        "warnings": f["warnings"],
        "chapter_memory_update": f["chapter_memory_update"],
        "adaptation_hints": {"global_rule": "所有改编建议必须基于 story_understanding 和 story_spine。"},
        "notes": ["01 已采用 01A–01F 分阶段解析结构。当前为 scaffold，后续每个阶段会接入不同 LLM 提示词。"],
        "config": config,
    }
