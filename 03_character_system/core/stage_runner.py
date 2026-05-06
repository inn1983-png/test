from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
llm_client_module = import_module("03_character_system.core.llm_client")
quality_checker = import_module("03_character_system.core.quality_checker")
json_repair = import_module("03_character_system.core.json_repair")
schema_validator = import_module("03_character_system.core.schema_validator")

SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_FINAL_REVISION_ROUNDS = 1

STAGES: list[dict[str, str]] = [
    {"stage_id": "03A", "name": "alias_merge_plan", "prompt_file": "prompts/03A_alias_merge_plan.md", "output_file": "03A_alias_merge_plan.json"},
    {"stage_id": "03B", "name": "character_cards", "prompt_file": "prompts/03B_character_cards.md", "output_file": "03B_character_cards.json"},
    {"stage_id": "03C", "name": "script_usage_binding", "prompt_file": "prompts/03C_script_usage_binding.md", "output_file": "03C_script_usage_binding.json"},
    {"stage_id": "03D", "name": "quality_check", "prompt_file": "prompts/03D_quality_check.md", "output_file": "03D_quality_check.json"},
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
    return {stage["stage_id"]: {} for stage in STAGES}


def _source_summary(novel_analysis: dict[str, Any], script: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_01": {
            "candidate_characters": novel_analysis.get("candidate_characters", []),
            "paragraphs": novel_analysis.get("paragraphs", []),
            "events": novel_analysis.get("events", []) or novel_analysis.get("event_graph", {}).get("events", []),
            "character_arc_map": novel_analysis.get("character_arc_map", []),
            "visual_risk_report": novel_analysis.get("visual_risk_report", {}),
        },
        "from_02": {
            "segments": script.get("segments", []),
            "character_name_usage": script.get("character_name_usage", []),
            "visual_dramatic_units": script.get("visual_dramatic_units", []),
            "storyboard_hints": script.get("storyboard_hints", []),
            "continuity_chain": script.get("continuity_chain", []),
        },
    }


def build_stage_payload(stage_id: str, novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], final_revision_context: dict[str, Any] | None = None) -> dict[str, Any]:
    source = _source_summary(novel_analysis, script)
    if stage_id == "03A":
        payload: dict[str, Any] = {"source": source, "task": "合并同一角色的不同称呼，输出别名归并计划。禁止按年龄、身份、昵称、职务拆新角色。"}
    elif stage_id == "03B":
        payload = {"source": source, "alias_merge_plan": outputs["03A"], "task": "生成稳定角色卡。只做角色资产标准化，不生成图片、分镜、图像提示词。"}
    elif stage_id == "03C":
        payload = {"source": source, "characters": outputs["03B"].get("characters", []), "task": "把角色库绑定到 02 剧本 usage，输出 script_usage_map 和覆盖报告，服务 06 单帧分镜引用稳定角色名。"}
    elif stage_id == "03D":
        payload = {"source": source, "stage_outputs": outputs, "task": "总检角色库是否去重正确、证据充分、描述稳定、不串脸、不污染，并可指定 retry_stages。"}
    else:
        raise ValueError(stage_id)
    if final_revision_context:
        payload["final_quality_revision_context"] = final_revision_context
    return payload


def _complete_json(client: Any, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    return client.complete_json(system_prompt, payload, repair_callback=lambda broken, error: json_repair.repair_json_with_llm(client, broken, error))


def _run_one_stage(client: Any, stage: dict[str, str], novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], output_dir: str | Path, max_retries: int, final_revision_context: dict[str, Any] | None = None) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    system_prompt = _read_prompt(stage["prompt_file"])
    payload = build_stage_payload(stage_id, novel_analysis, script, outputs, final_revision_context)
    attempts = []
    current_output: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    for attempt in range(1, max_retries + 2):
        if attempt == 1:
            current_output = _complete_json(client, system_prompt, payload)
        else:
            current_output = _complete_json(client, system_prompt, quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {}))
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


def _run_stage_range(client: Any, novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], output_dir: str | Path, start_index: int, max_retries: int, final_revision_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [_run_one_stage(client, stage, novel_analysis, script, outputs, output_dir, max_retries, final_revision_context) for stage in STAGES[start_index:]]


def _extract_retry_stage_ids(stage_d_output: dict[str, Any]) -> list[str]:
    quality_report = stage_d_output.get("quality_report", {}) if isinstance(stage_d_output, dict) else {}
    retry_stages = quality_report.get("retry_stages", []) if isinstance(quality_report, dict) else []
    return [stage_id for stage_id in retry_stages if stage_id in STAGE_INDEX and stage_id != "03D"]


def run_llm_stages(novel_analysis: dict[str, Any], script: dict[str, Any], output_dir: str | Path, max_retries: int = DEFAULT_MAX_RETRIES, max_final_revision_rounds: int = DEFAULT_MAX_FINAL_REVISION_ROUNDS) -> dict[str, Any]:
    if not novel_analysis or not script:
        raise RuntimeError("03_character_system requires 01 novel_analysis and 02 script.")
    client = llm_client_module.LLMClient()
    outputs = initial_context()
    stage_status = _run_stage_range(client, novel_analysis, script, outputs, output_dir, 0, max_retries)
    final_revision_rounds = []
    for round_index in range(1, max_final_revision_rounds + 1):
        retry_stage_ids = _extract_retry_stage_ids(outputs.get("03D", {}))
        if not retry_stage_ids:
            break
        start_index = min(STAGE_INDEX[stage_id] for stage_id in retry_stage_ids)
        quality_report = outputs.get("03D", {}).get("quality_report", {})
        final_revision_context = {"round": round_index, "retry_stage_ids": retry_stage_ids, "quality_report": quality_report, "instruction": "03D 总检要求重跑。请从最早问题阶段修正，并保持字段完整。"}
        rerun_status = _run_stage_range(client, novel_analysis, script, outputs, output_dir, start_index, max_retries, final_revision_context)
        final_revision_rounds.append({"round": round_index, "retry_stage_ids": retry_stage_ids, "rerun_status": rerun_status})
        stage_status.extend(rerun_status)
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "final_revision_rounds": final_revision_rounds, "outputs": outputs}


def merge_stage_outputs(novel_analysis: dict[str, Any], script: dict[str, Any], config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d = outputs["03A"], outputs["03B"], outputs["03C"], outputs["03D"]
    latest_status_by_stage = {item["stage_id"]: item for item in stage_result["stage_status"]}
    stage_scores = {stage_id: (item.get("quality") or {}).get("score") for stage_id, item in latest_status_by_stage.items()}
    quality_report = d.get("quality_report", {}) if isinstance(d.get("quality_report", {}), dict) else {}
    characters = b.get("characters", [])
    alias_index = {}
    for item in characters or []:
        if isinstance(item, dict):
            name = item.get("canonical_name", "")
            for alias in item.get("aliases", []) or []:
                alias_index[str(alias)] = name
            if name:
                alias_index[str(name)] = name
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "03_character_system",
        "status": "success",
        "stage_mode": "llm",
        "stage_status": stage_result["stage_status"],
        "final_revision_rounds": stage_result.get("final_revision_rounds", []),
        "source": {"required_upstream": ["01_novel_parser.novel_analysis.json", "02_script_writer.script.json"], "upstream_schema_versions": {"01": novel_analysis.get("schema_version"), "02": script.get("schema_version")}},
        "asset_scope": "character_standardization_only_no_image_no_storyboard_no_prompt",
        "character_alias_groups": a.get("character_alias_groups", []),
        "merge_policy": a.get("merge_policy", {}),
        "characters": characters,
        "alias_index": alias_index,
        "character_script_usage": c.get("script_usage_map", []),
        "coverage_report": c.get("coverage_report", {}),
        "risk_report": d.get("risk_report", b.get("risk_report", {})),
        "evidence_index": d.get("evidence_index", []),
        "revision_plan": d.get("revision_plan", {}),
        "warnings": d.get("warnings", []),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": ["03 只输出稳定角色库，供 06 单帧分镜引用；不生成图片、不生成分镜、不生成图像提示词。"],
        "config": config,
    }
    validation = schema_validator.validate_final_output(data)
    needs_review = any(item.get("status") != "success" for item in latest_status_by_stage.values()) or bool(quality_report.get("needs_retry")) or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
