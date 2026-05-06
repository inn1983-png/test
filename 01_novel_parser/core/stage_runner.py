from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
llm_client_module = import_module("01_novel_parser.core.llm_client")
quality_checker = import_module("01_novel_parser.core.quality_checker")

SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RETRIES = 2

STAGES: list[dict[str, str]] = [
    {"stage_id": "01A", "name": "story_understanding", "prompt_file": "prompts/01A_story_understanding.md", "output_file": "01A_story_understanding.json"},
    {"stage_id": "01B", "name": "paragraph_split", "prompt_file": "prompts/01B_paragraph_split.md", "output_file": "01B_paragraphs.json"},
    {"stage_id": "01C", "name": "event_graph", "prompt_file": "prompts/01C_event_graph.md", "output_file": "01C_event_graph.json"},
    {"stage_id": "01D", "name": "candidate_extract", "prompt_file": "prompts/01D_candidate_extract.md", "output_file": "01D_candidates.json"},
    {"stage_id": "01E", "name": "production_predict", "prompt_file": "prompts/01E_production_predict.md", "output_file": "01E_production_predict.json"},
    {"stage_id": "01F", "name": "quality_check", "prompt_file": "prompts/01F_quality_check.md", "output_file": "01F_quality_check.json"},
]


def _module_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _read_prompt(prompt_file: str) -> str:
    path = _module_dir() / prompt_file
    return io_utils.read_text(path, default="")


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
        "01B": {"schema_version": SCHEMA_VERSION, "stage": "01B_paragraph_split", "status": "scaffold", "chapters": [{"chapter_id": "chapter_001", "title": "占位章节", "paragraph_count": 0}], "paragraphs": [], "timeline": []},
        "01C": {"schema_version": SCHEMA_VERSION, "stage": "01C_event_graph", "status": "scaffold", "event_graph": {"events": [{"event_id": "event_001", "paragraph_ids": [], "summary": "占位事件"}], "event_edges": [], "main_event_path": ["event_001"], "side_event_paths": []}, "conflicts": [], "high_retention_segments": [], "scene_value_map": [], "character_arc_map": []},
        "01D": {"schema_version": SCHEMA_VERSION, "stage": "01D_candidate_extract", "status": "scaffold", "candidate_extraction_policy": {"mode": "extract_every_mentioned_candidate", "principle": "只要文章里提到过的人、地点、物件，都必须提取出来作为候选。"}, "candidate_characters": [], "candidate_scenes": [], "candidate_props": [], "asset_binding_hints": [], "visual_risk_report": {}},
        "01E": {"schema_version": SCHEMA_VERSION, "stage": "01E_production_predict", "status": "scaffold", "voice_line_candidates": [], "video_unit_candidates": [], "emotion_curve": [], "golden_lines": [], "confusion_risk_report": {}},
        "01F": {"schema_version": SCHEMA_VERSION, "stage": "01F_quality_check", "status": "scaffold", "evidence_index": [], "quality_report": {"input_text_length": len(novel_text), "source_status": source_status, "stage_mode": "scaffold", "needs_retry": False}, "warnings": ["当前为 scaffold 输出，01A–01F 尚未调用真实 LLM。"], "chapter_memory_update": {}},
    }


def build_stage_payload(stage_id: str, novel_text: str, outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if stage_id == "01A":
        return {"novel_text": novel_text}
    if stage_id == "01B":
        return {"novel_text": novel_text}
    if stage_id == "01C":
        return {"story_understanding": outputs["01A"].get("story_understanding"), "story_spine": outputs["01A"].get("story_spine"), "paragraphs": outputs["01B"].get("paragraphs")}
    if stage_id == "01D":
        return {"paragraphs": outputs["01B"].get("paragraphs"), "event_graph": outputs["01C"].get("event_graph"), "candidate_extraction_policy": outputs["01D"].get("candidate_extraction_policy")}
    if stage_id == "01E":
        return {"story_understanding": outputs["01A"].get("story_understanding"), "story_spine": outputs["01A"].get("story_spine"), "event_graph": outputs["01C"].get("event_graph"), "paragraphs": outputs["01B"].get("paragraphs"), "golden_lines_draft": outputs["01E"].get("golden_lines", [])}
    if stage_id == "01F":
        return {"novel_text": novel_text, "stage_outputs": outputs}
    raise ValueError(f"Unknown stage_id: {stage_id}")


def run_scaffold_stages(novel_text: str, output_dir: str | Path) -> dict[str, Any]:
    outputs = build_stage_outputs(novel_text)
    stage_status = []
    for stage in STAGES:
        quality = quality_checker.evaluate_stage(stage["stage_id"], outputs[stage["stage_id"]])
        outputs[stage["stage_id"]]["stage_quality"] = quality
        output_path = _write_stage(output_dir, stage["output_file"], outputs[stage["stage_id"]])
        stage_status.append({**stage, "status": "scaffold", "output_path": output_path, "quality": quality})
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "scaffold", "stage_status": stage_status, "outputs": outputs}


def run_llm_stages(novel_text: str, output_dir: str | Path, max_retries: int = DEFAULT_MAX_RETRIES) -> dict[str, Any]:
    client = llm_client_module.LLMClient()
    if not client.is_enabled():
        return run_scaffold_stages(novel_text, output_dir)

    outputs = build_stage_outputs(novel_text)
    stage_status = []
    for stage in STAGES:
        stage_id = stage["stage_id"]
        system_prompt = _read_prompt(stage["prompt_file"])
        payload = build_stage_payload(stage_id, novel_text, outputs)
        attempts = []
        current_output: dict[str, Any] | None = None
        quality: dict[str, Any] | None = None
        status = "success"

        for attempt in range(1, max_retries + 2):
            try:
                if attempt == 1:
                    current_output = client.complete_json(system_prompt, payload)
                else:
                    revision_payload = quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
                    current_output = client.complete_json(system_prompt, revision_payload)

                current_output.setdefault("schema_version", SCHEMA_VERSION)
                current_output.setdefault("stage", stage["name"])
                current_output["status"] = "llm"
                quality = quality_checker.evaluate_stage(stage_id, current_output)
                attempts.append({"attempt": attempt, "score": quality["score"], "passed": quality["passed"], "issues": quality["issues"], "revision_instructions": quality["revision_instructions"]})
                if quality["passed"]:
                    break
            except Exception as exc:
                status = "failed"
                attempts.append({"attempt": attempt, "error": str(exc), "passed": False})
                current_output = outputs[stage_id]
                quality = quality_checker.evaluate_stage(stage_id, current_output)
                break

        if current_output is None:
            current_output = outputs[stage_id]
            quality = quality_checker.evaluate_stage(stage_id, current_output)
            status = "failed"

        current_output["stage_quality"] = quality
        current_output["stage_attempts"] = attempts
        outputs[stage_id] = current_output
        output_path = _write_stage(output_dir, stage["output_file"], current_output)
        final_status = status if status == "failed" else ("success" if quality and quality.get("passed") else "needs_review")
        stage_status.append({**stage, "status": final_status, "output_path": output_path, "quality": quality, "attempts": attempts})

    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(novel_text: str, config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e, f = outputs["01A"], outputs["01B"], outputs["01C"], outputs["01D"], outputs["01E"], outputs["01F"]
    source_status = "input_found" if novel_text.strip() else "placeholder_input"
    event_graph = c.get("event_graph", {})
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result["stage_status"]}
    needs_review = any(item.get("status") != "success" for item in stage_result["stage_status"])
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "01_novel_parser",
        "status": "needs_review" if needs_review else "success",
        "source_status": source_status,
        "stage_mode": stage_result["stage_mode"],
        "stage_status": stage_result["stage_status"],
        "input": {"input_convention": "input/novel.txt", "source_file": "input/novel.txt", "raw_text_length": len(novel_text), "raw_text_preview": novel_text[:200]},
        "novel": {"title": "未命名小说", "language": "zh-CN", "genre_guess": "待真实解析", "narrative_pov": "待真实解析", "main_tense": "待真实解析"},
        "story_understanding": a.get("story_understanding", {}),
        "story_spine": a.get("story_spine", {}),
        "viewer_experience_plan": a.get("viewer_experience_plan", {}),
        "information_reveal_plan": a.get("information_reveal_plan", []),
        "adaptation_strategy": a.get("adaptation_strategy", {}),
        "misread_prevention": a.get("misread_prevention", {}),
        "chapters": b.get("chapters", []),
        "paragraphs": b.get("paragraphs", []),
        "timeline": b.get("timeline", []),
        "event_graph": event_graph,
        "events": event_graph.get("events", []) if isinstance(event_graph, dict) else [],
        "conflicts": c.get("conflicts", []),
        "high_retention_segments": c.get("high_retention_segments", []),
        "scene_value_map": c.get("scene_value_map", []),
        "character_arc_map": c.get("character_arc_map", []),
        "candidate_extraction_policy": d.get("candidate_extraction_policy", {}),
        "candidate_characters": d.get("candidate_characters", []),
        "candidate_scenes": d.get("candidate_scenes", []),
        "candidate_props": d.get("candidate_props", []),
        "asset_binding_hints": d.get("asset_binding_hints", []),
        "visual_risk_report": d.get("visual_risk_report", {}),
        "voice_line_candidates": e.get("voice_line_candidates", []),
        "video_unit_candidates": e.get("video_unit_candidates", []),
        "emotion_curve": e.get("emotion_curve", []),
        "golden_lines": e.get("golden_lines", []),
        "confusion_risk_report": e.get("confusion_risk_report", {}),
        "evidence_index": f.get("evidence_index", []),
        "quality_report": {**(f.get("quality_report", {}) if isinstance(f.get("quality_report", {}), dict) else {}), "stage_scores": stage_scores, "needs_review": needs_review},
        "warnings": f.get("warnings", []),
        "chapter_memory_update": f.get("chapter_memory_update", {}),
        "adaptation_hints": {"global_rule": "所有改编建议必须基于 story_understanding 和 story_spine。"},
        "notes": ["01 已采用 01A–01F 分阶段解析结构。开启 AI_DRAMA_01_USE_LLM=1 时，每阶段会真实调用本地 LLM，并根据评分和修改意见自动重跑。"],
        "config": config,
    }
