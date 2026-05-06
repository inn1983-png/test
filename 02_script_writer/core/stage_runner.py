from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
llm_client_module = import_module("02_script_writer.core.llm_client")
quality_checker = import_module("02_script_writer.core.quality_checker")
json_repair = import_module("02_script_writer.core.json_repair")
schema_validator = import_module("02_script_writer.core.schema_validator")

SCHEMA_VERSION = "1.0"
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_FINAL_REVISION_ROUNDS = 1

STAGES: list[dict[str, str]] = [
    {"stage_id": "02A", "name": "adaptation_blueprint", "prompt_file": "prompts/02A_adaptation_blueprint.md", "output_file": "02A_adaptation_blueprint.json"},
    {"stage_id": "02B", "name": "script_structure", "prompt_file": "prompts/02B_script_structure.md", "output_file": "02B_script_structure.json"},
    {"stage_id": "02C", "name": "script_draft", "prompt_file": "prompts/02C_script_draft.md", "output_file": "02C_script_draft.json"},
    {"stage_id": "02D", "name": "production_annotations", "prompt_file": "prompts/02D_production_annotations.md", "output_file": "02D_production_annotations.json"},
    {"stage_id": "02E", "name": "quality_check", "prompt_file": "prompts/02E_quality_check.md", "output_file": "02E_quality_check.json"},
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
        "02A": {},
        "02B": {},
        "02C": {},
        "02D": {},
        "02E": {},
    }


def build_stage_payload(
    stage_id: str,
    novel_analysis: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_summary = {
        "story_understanding": novel_analysis.get("story_understanding", {}),
        "story_spine": novel_analysis.get("story_spine", {}),
        "viewer_experience_plan": novel_analysis.get("viewer_experience_plan", {}),
        "information_reveal_plan": novel_analysis.get("information_reveal_plan", []),
        "adaptation_strategy": novel_analysis.get("adaptation_strategy", {}),
        "events": novel_analysis.get("events", []),
        "event_graph": novel_analysis.get("event_graph", {}),
        "conflicts": novel_analysis.get("conflicts", []),
        "high_retention_segments": novel_analysis.get("high_retention_segments", []),
        "scene_value_map": novel_analysis.get("scene_value_map", []),
        "character_arc_map": novel_analysis.get("character_arc_map", []),
        "golden_lines": novel_analysis.get("golden_lines", []),
        "voice_line_candidates": novel_analysis.get("voice_line_candidates", []),
        "video_unit_candidates": novel_analysis.get("video_unit_candidates", []),
        "emotion_curve": novel_analysis.get("emotion_curve", []),
        "visual_risk_report": novel_analysis.get("visual_risk_report", {}),
        "paragraphs": novel_analysis.get("paragraphs", []),
    }

    if stage_id == "02A":
        payload: dict[str, Any] = {
            "novel_analysis": source_summary,
            "task": "制定剧本改编蓝图，重点防止过度压缩，保留关键事件和高刺激冲突。",
        }
    elif stage_id == "02B":
        payload = {
            "novel_analysis": source_summary,
            "adaptation_blueprint": outputs["02A"],
            "task": "把改编蓝图拆成可写剧本的 scene_beats 和事件覆盖表。",
        }
    elif stage_id == "02C":
        payload = {
            "novel_analysis": source_summary,
            "adaptation_blueprint": outputs["02A"],
            "script_structure": outputs["02B"],
            "task": "生成正式剧本正文：对白 + OS + 留白 + 动作 + 情绪。",
        }
    elif stage_id == "02D":
        payload = {
            "novel_analysis": source_summary,
            "script_draft": outputs["02C"],
            "task": "为 08_audio 和 06_storyboard 生成生产标注。",
        }
    elif stage_id == "02E":
        payload = {
            "novel_analysis": source_summary,
            "stage_outputs": outputs,
            "task": "总检 02A-02D，判断是否压缩过狠、事件遗漏、对白/OS/留白不足，并给出重跑阶段。",
        }
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
    novel_analysis: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    output_dir: str | Path,
    max_retries: int,
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    system_prompt = _read_prompt(stage["prompt_file"])
    payload = build_stage_payload(stage_id, novel_analysis, outputs, final_revision_context)
    attempts = []
    current_output: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None

    for attempt in range(1, max_retries + 2):
        if attempt == 1:
            current_output = _complete_json(client, system_prompt, payload)
        else:
            revision_payload = quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
            current_output = _complete_json(client, system_prompt, revision_payload)

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


def _run_stage_range(client: Any, novel_analysis: dict[str, Any], outputs: dict[str, dict[str, Any]], output_dir: str | Path, start_index: int, max_retries: int, final_revision_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    statuses = []
    for stage in STAGES[start_index:]:
        statuses.append(_run_one_stage(client, stage, novel_analysis, outputs, output_dir, max_retries, final_revision_context))
    return statuses


def _extract_retry_stage_ids(stage_e_output: dict[str, Any]) -> list[str]:
    quality_report = stage_e_output.get("quality_report", {}) if isinstance(stage_e_output, dict) else {}
    retry_stages = quality_report.get("retry_stages", []) if isinstance(quality_report, dict) else []
    return [stage_id for stage_id in retry_stages if stage_id in STAGE_INDEX and stage_id != "02E"]


def run_llm_stages(novel_analysis: dict[str, Any], output_dir: str | Path, max_retries: int = DEFAULT_MAX_RETRIES, max_final_revision_rounds: int = DEFAULT_MAX_FINAL_REVISION_ROUNDS) -> dict[str, Any]:
    if not novel_analysis:
        raise RuntimeError("02_script_writer requires 01_novel_parser/novel_analysis.json.")

    client = llm_client_module.LLMClient()
    outputs = initial_context()
    stage_status = _run_stage_range(client, novel_analysis, outputs, output_dir, 0, max_retries)
    final_revision_rounds = []

    for round_index in range(1, max_final_revision_rounds + 1):
        retry_stage_ids = _extract_retry_stage_ids(outputs.get("02E", {}))
        if not retry_stage_ids:
            break
        start_index = min(STAGE_INDEX[stage_id] for stage_id in retry_stage_ids)
        quality_report = outputs.get("02E", {}).get("quality_report", {})
        final_revision_context = {"round": round_index, "retry_stage_ids": retry_stage_ids, "quality_report": quality_report, "instruction": "02E 总检要求重跑。请按 quality_report.revision_instructions 修正本阶段，并保持 JSON 字段完整。"}
        rerun_status = _run_stage_range(client, novel_analysis, outputs, output_dir, start_index, max_retries, final_revision_context)
        final_revision_rounds.append({"round": round_index, "retry_stage_ids": retry_stage_ids, "rerun_status": rerun_status})
        stage_status.extend(rerun_status)

    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "final_revision_rounds": final_revision_rounds, "outputs": outputs}


def build_script_text(segments: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in segments or []:
        if not isinstance(item, dict):
            continue
        stype = item.get("type")
        text = str(item.get("text", "")).strip()
        speaker = str(item.get("speaker", "")).strip()
        if stype == "os":
            lines.append(f"【OS】{text}")
        elif stype == "dialogue":
            lines.append(f"【{speaker or '角色'}】{text}")
        elif stype == "blank":
            lines.append("【留白】" + (text if text and text != "留白" else ""))
        elif stype == "action":
            lines.append(f"【动作】{text}")
        elif stype == "emotion":
            lines.append(f"【情绪】{text}")
    return "\n".join(line for line in lines if line.strip())


def merge_stage_outputs(novel_analysis: dict[str, Any], config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e = outputs["02A"], outputs["02B"], outputs["02C"], outputs["02D"], outputs["02E"]
    segments = c.get("segments", []) or []
    script_text = c.get("script_text") or build_script_text(segments)
    latest_status_by_stage = {item["stage_id"]: item for item in stage_result["stage_status"]}
    stage_scores = {stage_id: (item.get("quality") or {}).get("score") for stage_id, item in latest_status_by_stage.items()}
    quality_report = e.get("quality_report", {}) if isinstance(e.get("quality_report", {}), dict) else {}

    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "02_script_writer",
        "status": "success",
        "stage_mode": "llm",
        "stage_status": stage_result["stage_status"],
        "final_revision_rounds": stage_result.get("final_revision_rounds", []),
        "source": {
            "required_upstream": "01_novel_parser.novel_analysis.json",
            "upstream_schema_version": novel_analysis.get("schema_version"),
            "source_status": "input_found",
        },
        "script_id": c.get("script", {}).get("script_id") or "script_001",
        "title": c.get("script", {}).get("title") or c.get("title") or "未命名短剧剧本",
        "format": "dialogue_os_blank",
        "adaptation_blueprint": a.get("adaptation_blueprint", {}),
        "coverage_plan": a.get("coverage_plan", []),
        "tone_plan": a.get("tone_plan", {}),
        "compression_guardrails": a.get("compression_guardrails", {}),
        "script_structure": b.get("script_structure", {}),
        "scene_beats": b.get("scene_beats", []),
        "event_coverage_map": b.get("event_coverage_map", []),
        "retention_design": b.get("retention_design", {}),
        "script": c.get("script", {}),
        "segments": segments,
        "script_text": script_text,
        "production_annotations": d.get("production_annotations", {}),
        "audio_cues": d.get("audio_cues", []),
        "storyboard_hints": d.get("storyboard_hints", []),
        "risk_report": d.get("risk_report", {}),
        "evidence_index": e.get("evidence_index", []),
        "warnings": e.get("warnings", []),
        "revision_plan": e.get("revision_plan", {}),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": ["02 已采用真实 LLM 分阶段剧本改编；02E 总检可触发前置阶段重跑。"],
        "config": config,
    }
    validation = schema_validator.validate_final_output(data)
    needs_review = any(item.get("status") != "success" for item in latest_status_by_stage.values()) or bool(quality_report.get("needs_retry")) or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
