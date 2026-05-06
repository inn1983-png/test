from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
llm_client_module = import_module("01_novel_parser.core.llm_client")
quality_checker = import_module("01_novel_parser.core.quality_checker")
paragraph_splitter = import_module("01_novel_parser.core.paragraph_splitter")
chunk_manager = import_module("01_novel_parser.core.chunk_manager")
json_repair = import_module("01_novel_parser.core.json_repair")
schema_validator = import_module("01_novel_parser.core.schema_validator")

SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_FINAL_REVISION_ROUNDS = 1
DEFAULT_BATCH_MAX_CHARS = 6000

STAGES: list[dict[str, str]] = [
    {"stage_id": "01A", "name": "story_understanding", "prompt_file": "prompts/01A_story_understanding.md", "output_file": "01A_story_understanding.json"},
    {"stage_id": "01B", "name": "paragraph_split", "prompt_file": "prompts/01B_paragraph_split.md", "output_file": "01B_paragraphs.json"},
    {"stage_id": "01C", "name": "event_graph", "prompt_file": "prompts/01C_event_graph.md", "output_file": "01C_event_graph.json"},
    {"stage_id": "01D", "name": "candidate_extract", "prompt_file": "prompts/01D_candidate_extract.md", "output_file": "01D_candidates.json"},
    {"stage_id": "01E", "name": "production_predict", "prompt_file": "prompts/01E_production_predict.md", "output_file": "01E_production_predict.json"},
    {"stage_id": "01F", "name": "quality_check", "prompt_file": "prompts/01F_quality_check.md", "output_file": "01F_quality_check.json"},
]
STAGE_INDEX = {stage["stage_id"]: index for index, stage in enumerate(STAGES)}


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
    content = io_utils.read_text(path, default="").strip()
    if not content:
        raise RuntimeError(f"Missing prompt file content: {path}")
    return content


def initial_context() -> dict[str, dict[str, Any]]:
    return {
        "01A": {},
        "01B": {},
        "01C": {},
        "01D": {
            "candidate_extraction_policy": {
                "mode": "extract_every_mentioned_candidate",
                "principle": "只要文章里提到过的人、地点、物件，都必须提取出来作为候选。",
                "importance_rule": "importance 只能表示后续优先级，不能作为是否提取的门槛。",
            }
        },
        "01E": {"golden_lines": []},
        "01F": {},
    }


def build_stage_payload(
    stage_id: str,
    novel_text: str,
    outputs: dict[str, dict[str, Any]],
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if stage_id == "01A":
        payload: dict[str, Any] = {"novel_text": novel_text}
    elif stage_id == "01B":
        base = outputs.get("01B", {}).get("base_split") or paragraph_splitter.split_paragraphs(novel_text)
        payload = {"novel_text": novel_text, "base_split": base, "instruction": "保留 base_split 的 paragraph_id、text、start_char、end_char，只补充章节、段落类型和 timeline 标注。"}
    elif stage_id == "01C":
        payload = {
            "story_understanding": outputs["01A"].get("story_understanding"),
            "story_spine": outputs["01A"].get("story_spine"),
            "paragraphs": outputs["01B"].get("paragraphs"),
        }
    elif stage_id == "01D":
        payload = {
            "paragraphs": outputs["01B"].get("paragraphs"),
            "event_graph": outputs["01C"].get("event_graph"),
            "candidate_extraction_policy": outputs["01D"].get("candidate_extraction_policy"),
        }
    elif stage_id == "01E":
        payload = {
            "story_understanding": outputs["01A"].get("story_understanding"),
            "story_spine": outputs["01A"].get("story_spine"),
            "event_graph": outputs["01C"].get("event_graph"),
            "paragraphs": outputs["01B"].get("paragraphs"),
            "golden_lines_draft": outputs["01E"].get("golden_lines", []),
        }
    elif stage_id == "01F":
        payload = {"novel_text": novel_text, "stage_outputs": outputs}
    else:
        raise ValueError(f"Unknown stage_id: {stage_id}")

    if final_revision_context:
        payload["final_quality_revision_context"] = final_revision_context
    return payload


def _complete_json(client: Any, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    return client.complete_json(
        system_prompt,
        payload,
        repair_callback=lambda broken, error: json_repair.repair_json_with_llm(client, broken, error),
    )


def _run_one_stage(
    client: Any,
    stage: dict[str, str],
    novel_text: str,
    outputs: dict[str, dict[str, Any]],
    output_dir: str | Path,
    max_retries: int,
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    if stage_id == "01D":
        return _run_candidate_stage_in_batches(client, stage, novel_text, outputs, output_dir, max_retries, final_revision_context)

    system_prompt = _read_prompt(stage["prompt_file"])
    payload = build_stage_payload(stage_id, novel_text, outputs, final_revision_context)
    attempts = []
    current_output: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None

    for attempt in range(1, max_retries + 2):
        if attempt == 1:
            current_output = _complete_json(client, system_prompt, payload)
        else:
            revision_payload = quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
            current_output = _complete_json(client, system_prompt, revision_payload)

        if stage_id == "01B":
            base_split = payload.get("base_split") or paragraph_splitter.split_paragraphs(novel_text)
            current_output = paragraph_splitter.merge_llm_paragraph_annotations(base_split, current_output)
            current_output["base_split_locked"] = True

        current_output.setdefault("schema_version", SCHEMA_VERSION)
        current_output.setdefault("stage", stage["name"])
        current_output["status"] = "llm"
        quality = quality_checker.evaluate_stage(stage_id, current_output)
        attempts.append({"attempt": attempt, "score": quality["score"], "passed": quality["passed"], "issues": quality["issues"], "revision_instructions": quality["revision_instructions"]})
        if quality["passed"]:
            break

    if current_output is None or quality is None:
        raise RuntimeError(f"Stage {stage_id} did not produce output.")

    current_output["stage_quality"] = quality
    current_output["stage_attempts"] = attempts
    outputs[stage_id] = current_output
    output_path = _write_stage(output_dir, stage["output_file"], current_output)
    return {**stage, "status": "success" if quality.get("passed") else "needs_review", "output_path": output_path, "quality": quality, "attempts": attempts, "final_revision_context": final_revision_context}


def _run_candidate_stage_in_batches(
    client: Any,
    stage: dict[str, str],
    novel_text: str,
    outputs: dict[str, dict[str, Any]],
    output_dir: str | Path,
    max_retries: int,
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    system_prompt = _read_prompt(stage["prompt_file"])
    paragraphs = outputs.get("01B", {}).get("paragraphs", []) or []
    batches = chunk_manager.chunk_paragraphs(paragraphs, max_chars=DEFAULT_BATCH_MAX_CHARS)
    if not batches:
        raise RuntimeError("01D requires non-empty paragraphs from 01B.")

    batch_outputs = []
    batch_status = []
    base_policy = outputs.get("01D", {}).get("candidate_extraction_policy", {})

    for batch in batches:
        payload = {
            "batch_id": batch["batch_id"],
            "paragraphs": batch["paragraphs"],
            "event_graph": outputs["01C"].get("event_graph"),
            "candidate_extraction_policy": base_policy,
            "final_quality_revision_context": final_revision_context,
        }
        current_output: dict[str, Any] | None = None
        quality: dict[str, Any] | None = None
        attempts = []
        for attempt in range(1, max_retries + 2):
            if attempt == 1:
                current_output = _complete_json(client, system_prompt, payload)
            else:
                revision_payload = quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
                current_output = _complete_json(client, system_prompt, revision_payload)
            current_output["batch_id"] = batch["batch_id"]
            current_output.setdefault("schema_version", SCHEMA_VERSION)
            current_output.setdefault("stage", stage["name"])
            current_output["status"] = "llm"
            quality = quality_checker.evaluate_stage(stage_id, current_output)
            attempts.append({"attempt": attempt, "score": quality["score"], "passed": quality["passed"], "issues": quality["issues"], "revision_instructions": quality["revision_instructions"]})
            if quality["passed"]:
                break
        if current_output is None or quality is None:
            raise RuntimeError(f"Stage {stage_id} batch {batch['batch_id']} did not produce output.")
        batch_outputs.append(current_output)
        batch_status.append({"batch_id": batch["batch_id"], "quality": quality, "attempts": attempts, "status": "success" if quality.get("passed") else "needs_review"})
        _write_stage(output_dir, f"01D_{batch['batch_id']}_candidates.json", current_output)

    merged = chunk_manager.merge_candidate_batches(batch_outputs, base_policy)
    merged.update({"schema_version": SCHEMA_VERSION, "stage": stage["name"], "status": "llm", "batch_status": batch_status})
    quality = quality_checker.evaluate_stage(stage_id, merged)
    merged["stage_quality"] = quality
    outputs[stage_id] = merged
    output_path = _write_stage(output_dir, stage["output_file"], merged)
    return {**stage, "status": "success" if quality.get("passed") else "needs_review", "output_path": output_path, "quality": quality, "attempts": batch_status, "final_revision_context": final_revision_context}


def _run_stage_range(client: Any, novel_text: str, outputs: dict[str, dict[str, Any]], output_dir: str | Path, start_index: int, max_retries: int, final_revision_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    statuses = []
    for stage in STAGES[start_index:]:
        statuses.append(_run_one_stage(client, stage, novel_text, outputs, output_dir, max_retries, final_revision_context))
    return statuses


def _extract_retry_stage_ids(stage_f_output: dict[str, Any]) -> list[str]:
    quality_report = stage_f_output.get("quality_report", {}) if isinstance(stage_f_output, dict) else {}
    retry_stages = quality_report.get("retry_stages", []) if isinstance(quality_report, dict) else []
    return [stage_id for stage_id in retry_stages if stage_id in STAGE_INDEX and stage_id != "01F"]


def run_llm_stages(novel_text: str, output_dir: str | Path, max_retries: int = DEFAULT_MAX_RETRIES, max_final_revision_rounds: int = DEFAULT_MAX_FINAL_REVISION_ROUNDS) -> dict[str, Any]:
    if not novel_text.strip():
        raise RuntimeError("01_novel_parser requires input/novel.txt with non-empty content.")

    client = llm_client_module.LLMClient()
    outputs = initial_context()
    outputs["01B"]["base_split"] = paragraph_splitter.split_paragraphs(novel_text)
    stage_status = _run_stage_range(client, novel_text, outputs, output_dir, 0, max_retries)
    final_revision_rounds = []

    for round_index in range(1, max_final_revision_rounds + 1):
        retry_stage_ids = _extract_retry_stage_ids(outputs.get("01F", {}))
        if not retry_stage_ids:
            break
        start_index = min(STAGE_INDEX[stage_id] for stage_id in retry_stage_ids)
        quality_report = outputs.get("01F", {}).get("quality_report", {})
        final_revision_context = {"round": round_index, "retry_stage_ids": retry_stage_ids, "quality_report": quality_report, "instruction": "01F 总检要求重跑。请按 quality_report.revision_instructions 修正本阶段，并保持 JSON 字段完整。"}
        rerun_status = _run_stage_range(client, novel_text, outputs, output_dir, start_index, max_retries, final_revision_context)
        final_revision_rounds.append({"round": round_index, "retry_stage_ids": retry_stage_ids, "rerun_status": rerun_status})
        stage_status.extend(rerun_status)

    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "final_revision_rounds": final_revision_rounds, "outputs": outputs}


def merge_stage_outputs(novel_text: str, config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e, f = outputs["01A"], outputs["01B"], outputs["01C"], outputs["01D"], outputs["01E"], outputs["01F"]
    event_graph = c.get("event_graph", {})
    latest_status_by_stage = {item["stage_id"]: item for item in stage_result["stage_status"]}
    stage_scores = {stage_id: (item.get("quality") or {}).get("score") for stage_id, item in latest_status_by_stage.items()}
    quality_report = f.get("quality_report", {}) if isinstance(f.get("quality_report", {}), dict) else {}
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "01_novel_parser",
        "status": "success",
        "source_status": "input_found",
        "stage_mode": "llm",
        "stage_status": stage_result["stage_status"],
        "final_revision_rounds": stage_result.get("final_revision_rounds", []),
        "input": {"input_convention": "input/novel.txt", "source_file": "input/novel.txt", "raw_text_length": len(novel_text), "raw_text_preview": novel_text[:200]},
        "novel": f.get("novel", {"title": "未命名小说", "language": "zh-CN"}),
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
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "warnings": f.get("warnings", []),
        "chapter_memory_update": f.get("chapter_memory_update", {}),
        "adaptation_hints": {"global_rule": "所有改编建议必须基于 story_understanding 和 story_spine。"},
        "notes": ["01 已采用真实 LLM 分阶段解析；01B 使用程序段落边界，01D 分批提取候选，最终执行硬规则校验。"],
        "config": config,
    }
    validation = schema_validator.validate_final_output(data)
    needs_review = any(item.get("status") != "success" for item in latest_status_by_stage.values()) or bool(quality_report.get("needs_retry")) or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
