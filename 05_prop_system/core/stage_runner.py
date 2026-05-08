from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
stage_status_writer = import_module("00_common.stage_status")
stage_cache = import_module("00_common.stage_cache")
llm_client_module = import_module("05_prop_system.core.llm_client")
quality_checker = import_module("05_prop_system.core.quality_checker")
json_repair = import_module("05_prop_system.core.json_repair")
schema_validator = import_module("05_prop_system.core.schema_validator")

SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_FINAL_REVISION_ROUNDS = 1

STAGES: list[dict[str, str]] = [
    {"stage_id": "05A", "name": "prop_merge_plan", "prompt_file": "prompts/05A_prop_merge_plan.md", "output_file": "05A_prop_merge_plan.json"},
    {"stage_id": "05B", "name": "prop_cards", "prompt_file": "prompts/05B_prop_cards.md", "output_file": "05B_prop_cards.json"},
    {"stage_id": "05C", "name": "script_usage_binding", "prompt_file": "prompts/05C_script_usage_binding.md", "output_file": "05C_script_usage_binding.json"},
    {"stage_id": "05D", "name": "quality_check", "prompt_file": "prompts/05D_quality_check.md", "output_file": "05D_quality_check.json"},
    {"stage_id": "05E", "name": "asset_review", "prompt_file": "prompts/05E_asset_review.md", "output_file": "05E_asset_review.json"},
]
STAGE_INDEX = {stage["stage_id"]: index for index, stage in enumerate(STAGES)}
REVIEW_STAGE_ID = "05E"


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
        "from_01_understanding": {
            "story_understanding": novel_analysis.get("story_understanding", {}),
            "story_spine": novel_analysis.get("story_spine", {}),
            "events": novel_analysis.get("events", []) or novel_analysis.get("event_graph", {}).get("events", []),
            "event_graph": novel_analysis.get("event_graph", {}),
            "conflicts": novel_analysis.get("conflicts", []),
            "high_retention_segments": novel_analysis.get("high_retention_segments", []),
            "asset_binding_hints": novel_analysis.get("asset_binding_hints", []),
            "visual_risk_report": novel_analysis.get("visual_risk_report", {}),
        },
        "from_01_candidates": {
            "candidate_props": novel_analysis.get("candidate_props", []),
            "paragraphs": novel_analysis.get("paragraphs", []),
        },
        "from_02_script": {
            "segments": script.get("segments", []),
            "visual_dramatic_units": script.get("visual_dramatic_units", []),
            "storyboard_hints": script.get("storyboard_hints", []),
            "scene_beats": script.get("scene_beats", []),
            "continuity_chain": script.get("continuity_chain", []),
        },
    }


def build_stage_payload(stage_id: str, novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], final_revision_context: dict[str, Any] | None = None) -> dict[str, Any]:
    source = _source_summary(novel_analysis, script)
    if stage_id == "05A":
        payload: dict[str, Any] = {"source": source, "task": "合并同一道具的不同说法，区分关键道具、动作道具、背景物件，输出道具归并计划。"}
    elif stage_id == "05B":
        payload = {"source": source, "prop_merge_plan": outputs["05A"], "task": "生成稳定道具卡、资产分级、重要性评分和参考图计划。只做道具资产标准化，不生成图片、分镜、图像提示词。"}
    elif stage_id == "05C":
        payload = {"source": source, "props": outputs["05B"].get("props", []), "task": "把道具库绑定到 02 剧本使用，输出 script_usage_map 和覆盖报告，服务 06 单帧分镜引用稳定道具名。"}
    elif stage_id == "05D":
        payload = {"source": source, "stage_outputs": outputs, "task": "总检道具库是否去重正确、类型清晰、归属合理、证据充分，并可指定 retry_stages。"}
    elif stage_id == "05E":
        payload = {"source": source, "stage_outputs": outputs, "task": "站在 06 单帧分镜角度进行资产复核。必须使用 01 story_understanding/story_spine/events/conflicts/asset_binding_hints 判断遗漏、误合并、误分级、过度资产化，并输出 downstream_readiness_for_06。"}
    else:
        raise ValueError(stage_id)
    if final_revision_context:
        payload["final_quality_revision_context"] = final_revision_context
    return payload


def _complete_json(client: Any, system_prompt: str, payload: dict[str, Any], trace_label: str) -> dict[str, Any]:
    return client.complete_json(system_prompt, payload, repair_callback=lambda broken, error: json_repair.repair_json_with_llm(client, broken, error), trace_label=trace_label)


def _run_one_stage(client: Any, stage: dict[str, str], novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], output_dir: str | Path, max_retries: int, final_revision_context: dict[str, Any] | None = None, force: bool = False, force_stages: list[str] | None = None) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    skip, cached = stage_cache.should_skip_stage(output_dir, stage_id, stage["output_file"], force=force, force_stages=force_stages)
    if skip and cached is not None:
        outputs[stage_id] = cached
        quality = cached.get("stage_quality", {})
        status = "success" if quality.get("passed") else "needs_review"
        print(f"[RESUME] {stage_id} skipped (cached, score={quality.get('score', '?')})")
        return {**stage, "status": status, "output_path": str(_intermediate_dir(output_dir) / stage["output_file"]), "quality": quality, "attempts": cached.get("stage_attempts", []), "final_revision_context": final_revision_context}

    stage_status_writer.mark_stage_started("05_prop_system", output_dir, stage_id, stage["name"], "stage started")
    system_prompt = _read_prompt(stage["prompt_file"])
    payload = build_stage_payload(stage_id, novel_analysis, script, outputs, final_revision_context)
    attempts = []
    current_output: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    for attempt in range(1, max_retries + 2):
        trace_label = f"{stage_id}_attempt_{attempt}"
        revision_payload = payload if attempt == 1 else quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
        current_output = _complete_json(client, system_prompt, revision_payload, trace_label=trace_label)
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
    status = "success" if quality.get("passed") else "needs_review"
    stage_status_writer.mark_stage_finished(
        "05_prop_system",
        output_dir,
        stage_id,
        stage["name"],
        status,
        output_file=output_path,
        score=quality.get("score"),
        issues_count=len(quality.get("issues", []) or []),
    )
    return {**stage, "status": status, "output_path": output_path, "quality": quality, "attempts": attempts, "final_revision_context": final_revision_context}


def _run_stage_range(client: Any, novel_analysis: dict[str, Any], script: dict[str, Any], outputs: dict[str, dict[str, Any]], output_dir: str | Path, start_index: int, max_retries: int, final_revision_context: dict[str, Any] | None = None, force: bool = False, force_stages: list[str] | None = None) -> list[dict[str, Any]]:
    return [_run_one_stage(client, stage, novel_analysis, script, outputs, output_dir, max_retries, final_revision_context, force=force, force_stages=force_stages) for stage in STAGES[start_index:]]


def _extract_retry_stage_ids(outputs: dict[str, Any]) -> list[str]:
    retry_stage_ids: list[str] = []
    for stage_id, report_key in [("05D", "quality_report"), ("05E", "review_report")]:
        report = outputs.get(stage_id, {}).get(report_key, {}) if isinstance(outputs.get(stage_id), dict) else {}
        if isinstance(report, dict):
            retry_stage_ids.extend(report.get("retry_stages", []) or [])
    return [stage_id for stage_id in retry_stage_ids if stage_id in STAGE_INDEX and stage_id != REVIEW_STAGE_ID]


def run_llm_stages(novel_analysis: dict[str, Any], script: dict[str, Any], output_dir: str | Path, max_retries: int = DEFAULT_MAX_RETRIES, max_final_revision_rounds: int = DEFAULT_MAX_FINAL_REVISION_ROUNDS, resume: bool = False, force: bool = False, force_stages: list[str] | None = None) -> dict[str, Any]:
    if not novel_analysis or not script:
        raise RuntimeError("05_prop_system requires 01 novel_analysis and 02 script.")
    client = llm_client_module.LLMClient()
    if hasattr(client, "set_trace_output_dir"):
        client.set_trace_output_dir(output_dir)
    outputs = initial_context()

    start_index = 0
    if resume and not force:
        cached = stage_cache.load_cached_outputs(output_dir, STAGES, force=force, force_stages=force_stages)
        for sid, data in cached.items():
            outputs[sid] = data
        start_index = stage_cache.find_resume_start_index(STAGES, cached, STAGE_INDEX)
        if start_index > 0:
            print(f"[RESUME] 05_prop_system resuming from stage index {start_index} ({STAGES[start_index]['stage_id'] if start_index < len(STAGES) else 'done'})")

    stage_status = _run_stage_range(client, novel_analysis, script, outputs, output_dir, start_index, max_retries, force=force, force_stages=force_stages)
    final_revision_rounds = []
    for round_index in range(1, max_final_revision_rounds + 1):
        retry_stage_ids = _extract_retry_stage_ids(outputs)
        if not retry_stage_ids:
            break
        start_index = min(STAGE_INDEX[stage_id] for stage_id in retry_stage_ids)
        review_context = outputs.get("05E", {}).get("review_report", {})
        quality_context = outputs.get("05D", {}).get("quality_report", {})
        final_revision_context = {"round": round_index, "retry_stage_ids": retry_stage_ids, "quality_report": quality_context, "review_report": review_context, "instruction": "05D/05E 要求重跑。请从最早问题阶段修正，并保持字段完整。"}
        revision_force_stages = list(set((force_stages or []) + retry_stage_ids))
        rerun_status = _run_stage_range(client, novel_analysis, script, outputs, output_dir, start_index, max_retries, final_revision_context, force=force, force_stages=revision_force_stages)
        final_revision_rounds.append({"round": round_index, "retry_stage_ids": retry_stage_ids, "rerun_status": rerun_status})
        stage_status.extend(rerun_status)
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "final_revision_rounds": final_revision_rounds, "outputs": outputs}


def merge_stage_outputs(novel_analysis: dict[str, Any], script: dict[str, Any], config: dict[str, Any], stage_result: dict[str, Any]) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e = outputs["05A"], outputs["05B"], outputs["05C"], outputs["05D"], outputs["05E"]
    latest_status_by_stage = {item["stage_id"]: item for item in stage_result["stage_status"]}
    stage_scores = {stage_id: (item.get("quality") or {}).get("score") for stage_id, item in latest_status_by_stage.items()}
    quality_report = d.get("quality_report", {}) if isinstance(d.get("quality_report", {}), dict) else {}
    review_report = e.get("review_report", {}) if isinstance(e.get("review_report", {}), dict) else {}
    props = b.get("props", [])
    alias_index = {}
    for item in props or []:
        if isinstance(item, dict):
            name = item.get("canonical_prop_name", "")
            for alias in item.get("aliases", []) or []:
                alias_index[str(alias)] = name
            if name:
                alias_index[str(name)] = name
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "05_prop_system",
        "status": "success",
        "stage_mode": "llm",
        "stage_status": stage_result["stage_status"],
        "final_revision_rounds": stage_result.get("final_revision_rounds", []),
        "source": {"required_upstream": ["01_novel_parser.novel_analysis.json", "02_script_writer.script.json"], "upstream_schema_versions": {"01": novel_analysis.get("schema_version"), "02": script.get("schema_version")}},
        "asset_scope": "prop_standardization_only_no_image_no_storyboard_no_prompt",
        "prop_alias_groups": a.get("prop_alias_groups", []),
        "merge_policy": a.get("merge_policy", {}),
        "props": props,
        "prop_alias_index": alias_index,
        "prop_script_usage": c.get("script_usage_map", []),
        "coverage_report": c.get("coverage_report", {}),
        "asset_review_report": review_report,
        "downstream_readiness_for_06": e.get("downstream_readiness_for_06", {}),
        "main_assets_for_06": e.get("main_assets_for_06", []),
        "optional_assets_for_06": e.get("optional_assets_for_06", []),
        "do_not_reference_as_main_asset": e.get("do_not_reference_as_main_asset", []),
        "upstream_blocking_issues": e.get("upstream_blocking_issues", []),
        "risk_report": d.get("risk_report", b.get("risk_report", {})),
        "evidence_index": d.get("evidence_index", []),
        "revision_plan": d.get("revision_plan", {}),
        "warnings": list(d.get("warnings", [])) + list(e.get("warnings", [])),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": ["05 只输出稳定道具库，供 06 单帧分镜引用；不生成图片、不生成分镜、不生成图像提示词。"],
        "config": config,
    }
    validation = schema_validator.validate_final_output(data)
    needs_review = any(item.get("status") != "success" for item in latest_status_by_stage.values()) or bool(quality_report.get("needs_retry")) or bool(review_report.get("needs_retry")) or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
