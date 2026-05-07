from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
stage_status_writer = import_module("00_common.stage_status")
llm_client_module = import_module("06_storyboard.core.llm_client")
quality_checker = import_module("06_storyboard.core.quality_checker")
json_repair = import_module("06_storyboard.core.json_repair")
schema_validator = import_module("06_storyboard.core.schema_validator")

SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_FINAL_REVISION_ROUNDS = 1

STAGES: list[dict[str, str]] = [
    {"stage_id": "06A", "name": "asset_gate", "prompt_file": "prompts/06A_asset_gate.md", "output_file": "06A_asset_gate.json"},
    {"stage_id": "06B", "name": "storyboard_plan", "prompt_file": "prompts/06B_storyboard_plan.md", "output_file": "06B_storyboard_plan.json"},
    {"stage_id": "06C", "name": "single_frame_storyboard", "prompt_file": "prompts/06C_single_frame_storyboard.md", "output_file": "06C_single_frame_storyboard.json"},
    {"stage_id": "06D", "name": "continuity_binding", "prompt_file": "prompts/06D_continuity_binding.md", "output_file": "06D_continuity_binding.json"},
    {"stage_id": "06E", "name": "quality_check", "prompt_file": "prompts/06E_quality_check.md", "output_file": "06E_quality_check.json"},
]
STAGE_INDEX = {stage["stage_id"]: index for index, stage in enumerate(STAGES)}
FINAL_STAGE_ID = "06E"


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


def _name_list(items: list[Any], key: str) -> list[str]:
    names: list[str] = []
    for item in items or []:
        if isinstance(item, dict) and item.get(key):
            names.append(str(item[key]))
    return names


def _character_costumes(characters: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in characters.get("characters", []) or []:
        if not isinstance(item, dict):
            continue
        name = item.get("canonical_name")
        if not name:
            continue
        costume_ids = []
        for costume in item.get("costume_variants", []) or []:
            if isinstance(costume, dict) and costume.get("costume_id"):
                costume_ids.append(str(costume["costume_id"]))
        rows.append({"canonical_name": str(name), "costume_ids": costume_ids, "default_costume_id": item.get("default_costume_id", "")})
    return rows


def _prop_names_by_policy(props: dict[str, Any], policies: set[str]) -> list[str]:
    names: list[str] = []
    for item in props.get("props", []) or []:
        if isinstance(item, dict) and item.get("canonical_prop_name") and item.get("wearable_policy") in policies:
            names.append(str(item["canonical_prop_name"]))
    return names


def _asset_summary(characters: dict[str, Any], scenes: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    return {
        "characters": characters.get("characters", []),
        "scenes": scenes.get("scenes", []),
        "props": props.get("props", []),
        "allowed_asset_names": {
            "characters": _name_list(characters.get("characters", []), "canonical_name"),
            "character_costumes": _character_costumes(characters),
            "scenes": _name_list(scenes.get("scenes", []), "canonical_scene_name"),
            "props": _name_list(props.get("props", []), "canonical_prop_name"),
            "mergeable_wearable_props": _prop_names_by_policy(props, {"merge_into_appearance_asset", "both"}),
            "independent_prop_refs": _prop_names_by_policy(props, {"not_wearable", "independent_prop_reference", "both"}),
        },
        "asset_readiness": {
            "characters": characters.get("downstream_readiness_for_06", {}),
            "scenes": scenes.get("downstream_readiness_for_06", {}),
            "props": props.get("downstream_readiness_for_06", {}),
        },
        "main_assets_for_06": {
            "characters": characters.get("main_assets_for_06", []),
            "scenes": scenes.get("main_assets_for_06", []),
            "props": props.get("main_assets_for_06", []),
        },
        "optional_assets_for_06": {
            "characters": characters.get("optional_assets_for_06", []),
            "scenes": scenes.get("optional_assets_for_06", []),
            "props": props.get("optional_assets_for_06", []),
        },
        "do_not_reference_as_main_asset": {
            "characters": characters.get("do_not_reference_as_main_asset", []),
            "scenes": scenes.get("do_not_reference_as_main_asset", []),
            "props": props.get("do_not_reference_as_main_asset", []),
        },
        "upstream_blocking_issues": {
            "characters": characters.get("upstream_blocking_issues", []),
            "scenes": scenes.get("upstream_blocking_issues", []),
            "props": props.get("upstream_blocking_issues", []),
        },
    }


def _source_summary(script: dict[str, Any], characters: dict[str, Any], scenes: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_02_script": {
            "script_id": script.get("script_id"),
            "title": script.get("title"),
            "segments": script.get("segments", []),
            "voice_line_plan": script.get("voice_line_plan", []),
            "scene_beats": script.get("scene_beats", []),
            "visual_dramatic_units": script.get("visual_dramatic_units", []),
            "appearance_state_changes": script.get("appearance_state_changes", []),
            "storyboard_hints": script.get("storyboard_hints", []),
            "continuity_chain": script.get("continuity_chain", []),
            "event_coverage_map": script.get("event_coverage_map", []),
            "character_name_usage": script.get("character_name_usage", []),
            "risk_report": script.get("risk_report", {}),
        },
        "from_03_04_05_assets": _asset_summary(characters, scenes, props),
    }


def build_stage_payload(
    stage_id: str,
    script: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = _source_summary(script, characters, scenes, props)
    if stage_id == "06A":
        payload: dict[str, Any] = {
            "source": source,
            "task": "检查 02 剧本中的角色/服装/场景/道具需求是否都能被 03/04/05 稳定资产库覆盖。必须参考 02 appearance_state_changes 判断换装和穿戴状态。不能新增资产；缺资产或 costume_id 必须输出 upstream_blocking_issues，并建议对应 03/04/05 阶段重跑。",
        }
    elif stage_id == "06B":
        payload = {
            "source": source,
            "asset_gate": outputs["06A"],
            "task": "基于 02 剧本、02 appearance_state_changes 和 06A 允许资产清单，规划单帧分镜组、覆盖范围、帧数密度和连续性策略。不要生成图片提示词。",
        }
    elif stage_id == "06C":
        payload = {
            "source": source,
            "asset_gate": outputs["06A"],
            "storyboard_plan": outputs["06B"],
            "task": "生成正式单帧分镜 JSON。每一帧只能引用 allowed_asset_names 中的稳定角色名、角色 costume_id、稳定场景名、稳定道具名；必须依据 02 appearance_state_changes 输出 character_lock_reference 与 appearance_asset_requirements，但不要写图像提示词。",
        }
    elif stage_id == "06D":
        payload = {
            "source": source,
            "asset_gate": outputs["06A"],
            "storyboard_plan": outputs["06B"],
            "frames": outputs["06C"].get("frames", []),
            "appearance_asset_requirements": outputs["06C"].get("appearance_asset_requirements", []),
            "task": "为单帧分镜补充连续性绑定、上一帧/下一帧承接、四宫格预览组。必须检查同一角色 costume_id/appearance_asset_key 的连续性。四宫格只是检查单位，不是图片生成。",
        }
    elif stage_id == "06E":
        payload = {
            "source": source,
            "stage_outputs": outputs,
            "task": "总检 06 单帧分镜：资产引用、角色定妆照引用、角色造型引用、02 appearance_state_changes 覆盖、剧情覆盖、顺序、连续性、07 可用性、越界字段、缺资产阻塞问题，并可指定 retry_stages。",
        }
    else:
        raise ValueError(stage_id)
    if final_revision_context:
        payload["final_quality_revision_context"] = final_revision_context
    return payload


def _complete_json(client: Any, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
    return client.complete_json(system_prompt, payload, repair_callback=lambda broken, error: json_repair.repair_json_with_llm(client, broken, error))


def _run_one_stage(
    client: Any,
    stage: dict[str, str],
    script: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    output_dir: str | Path,
    max_retries: int,
    final_revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    stage_status_writer.mark_stage_started("06_storyboard", output_dir, stage_id, stage["name"], "stage started")
    system_prompt = _read_prompt(stage["prompt_file"])
    payload = build_stage_payload(stage_id, script, characters, scenes, props, outputs, final_revision_context)
    attempts = []
    current_output: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    for attempt in range(1, max_retries + 2):
        revision_payload = payload if attempt == 1 else quality_checker.build_revision_payload(stage_id, payload, current_output or {}, quality or {})
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
    status = "success" if quality.get("passed") else "needs_review"
    stage_status_writer.mark_stage_finished(
        "06_storyboard",
        output_dir,
        stage_id,
        stage["name"],
        status,
        output_file=output_path,
        score=quality.get("score"),
        issues_count=len(quality.get("issues", []) or []),
    )
    return {**stage, "status": status, "output_path": output_path, "quality": quality, "attempts": attempts, "final_revision_context": final_revision_context}


def _run_stage_range(
    client: Any,
    script: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    output_dir: str | Path,
    start_index: int,
    max_retries: int,
    final_revision_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        _run_one_stage(client, stage, script, characters, scenes, props, outputs, output_dir, max_retries, final_revision_context)
        for stage in STAGES[start_index:]
    ]


def _extract_retry_stage_ids(outputs: dict[str, Any]) -> list[str]:
    retry_stage_ids: list[str] = []
    for stage_id, report_key in [("06D", "frame_transition_report"), ("06E", "quality_report")]:
        report = outputs.get(stage_id, {}).get(report_key, {}) if isinstance(outputs.get(stage_id), dict) else {}
        if isinstance(report, dict):
            retry_stage_ids.extend(report.get("retry_stages", []) or [])
    return [stage_id for stage_id in retry_stage_ids if stage_id in STAGE_INDEX and stage_id != FINAL_STAGE_ID]


def run_llm_stages(
    script: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    output_dir: str | Path,
    max_retries: int = DEFAULT_MAX_RETRIES,
    max_final_revision_rounds: int = DEFAULT_MAX_FINAL_REVISION_ROUNDS,
) -> dict[str, Any]:
    if not script or not characters or not scenes or not props:
        raise RuntimeError("06_storyboard requires 02 script, 03 characters, 04 scenes and 05 props.")
    client = llm_client_module.LLMClient()
    outputs = initial_context()
    stage_status = _run_stage_range(client, script, characters, scenes, props, outputs, output_dir, 0, max_retries)
    final_revision_rounds = []
    for round_index in range(1, max_final_revision_rounds + 1):
        retry_stage_ids = _extract_retry_stage_ids(outputs)
        if not retry_stage_ids:
            break
        start_index = min(STAGE_INDEX[stage_id] for stage_id in retry_stage_ids)
        final_revision_context = {
            "round": round_index,
            "retry_stage_ids": retry_stage_ids,
            "quality_report": outputs.get("06E", {}).get("quality_report", {}),
            "frame_transition_report": outputs.get("06D", {}).get("frame_transition_report", {}),
            "instruction": "06D/06E 要求重跑。请从最早问题阶段修正，并保持字段完整。不得新增资产或输出图像提示词。",
        }
        rerun_status = _run_stage_range(client, script, characters, scenes, props, outputs, output_dir, start_index, max_retries, final_revision_context)
        final_revision_rounds.append({"round": round_index, "retry_stage_ids": retry_stage_ids, "rerun_status": rerun_status})
        stage_status.extend(rerun_status)
    return {"schema_version": SCHEMA_VERSION, "stage_mode": "llm", "stage_status": stage_status, "final_revision_rounds": final_revision_rounds, "outputs": outputs}


def merge_stage_outputs(
    script: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    config: dict[str, Any],
    stage_result: dict[str, Any],
) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a, b, c, d, e = outputs["06A"], outputs["06B"], outputs["06C"], outputs["06D"], outputs["06E"]
    latest_status_by_stage = {item["stage_id"]: item for item in stage_result["stage_status"]}
    stage_scores = {stage_id: (item.get("quality") or {}).get("score") for stage_id, item in latest_status_by_stage.items()}
    quality_report = e.get("quality_report", {}) if isinstance(e.get("quality_report", {}), dict) else {}
    allowed_asset_names = a.get("allowed_asset_names", _asset_summary(characters, scenes, props).get("allowed_asset_names", {}))
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "06_storyboard",
        "status": "success",
        "stage_mode": "llm",
        "stage_status": stage_result["stage_status"],
        "final_revision_rounds": stage_result.get("final_revision_rounds", []),
        "source": {
            "required_upstream": [
                "02_script_writer.script.json",
                "03_character_system.characters.json",
                "04_scene_system.scenes.json",
                "05_prop_system.props.json",
            ],
            "upstream_schema_versions": {
                "02": script.get("schema_version"),
                "03": characters.get("schema_version"),
                "04": scenes.get("schema_version"),
                "05": props.get("schema_version"),
            },
        },
        "asset_scope": "single_frame_storyboard_only_no_image_no_comfyui_no_video_prompt",
        "allowed_asset_names": allowed_asset_names,
        "asset_availability_report": a.get("asset_availability_report", {}),
        "storyboard_scope": a.get("storyboard_scope", {}),
        "upstream_blocking_issues": list(a.get("upstream_blocking_issues", [])) + list(e.get("upstream_blocking_issues", [])),
        "storyboard_plan": b.get("storyboard_plan", {}),
        "frame_group_plan": b.get("frame_group_plan", []),
        "coverage_plan": b.get("coverage_plan", []),
        "appearance_asset_requirements": c.get("appearance_asset_requirements", []),
        "frames": c.get("frames", []),
        "continuity_map": d.get("continuity_map", []),
        "four_grid_preview_groups": d.get("four_grid_preview_groups", []),
        "frame_transition_report": d.get("frame_transition_report", {}),
        "reference_requirements_summary": e.get("reference_requirements_summary", {}),
        "evidence_index": e.get("evidence_index", []),
        "revision_plan": e.get("revision_plan", {}),
        "warnings": list(b.get("warnings", [])) + list(c.get("warnings", [])) + list(d.get("warnings", [])) + list(e.get("warnings", [])),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": [
            "06 只输出单帧分镜 JSON，服务 07 图片生成；不生成图片、不调用 ComfyUI、不生成最终视频。",
            "06 分镜只能引用 03/04/05 稳定资产名和 03 costume_id；缺资产必须通过 upstream_blocking_issues 建议上游重跑。",
            "appearance_asset_requirements 是 07 后续先生成角色定妆/造型参考图的需求索引，不是图片输出。",
        ],
        "config": config,
    }
    assets = {"characters": characters.get("characters", []), "scenes": scenes.get("scenes", []), "props": props.get("props", [])}
    validation = schema_validator.validate_final_output(data, assets=assets)
    needs_review = (
        any(item.get("status") != "success" for item in latest_status_by_stage.values())
        or bool(quality_report.get("needs_retry"))
        or bool(data.get("upstream_blocking_issues"))
        or not validation["passed"]
    )
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
