from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
stage_status_writer = import_module("00_common.stage_status")
quality_checker = import_module("07_storyboard_image.core.quality_checker")
schema_validator = import_module("07_storyboard_image.core.schema_validator")
planner = import_module("07_storyboard_image.core.planner")
image_registry = import_module("07_storyboard_image.core.image_registry")
retry_manager = import_module("07_storyboard_image.core.retry_manager")
phase_07a = import_module("07_storyboard_image.stages.phase_07a_character_lock")
phase_07b = import_module("07_storyboard_image.stages.phase_07b_character_appearance")
phase_07c = import_module("07_storyboard_image.stages.phase_07c_reference_assets")
phase_07d = import_module("07_storyboard_image.stages.phase_07d_storyboard_frame")

SCHEMA_VERSION = "1.1"

STAGES: list[dict[str, str]] = [
    {"stage_id": "07P", "name": "plan_dependency_graph", "output_file": "07P_plan.json"},
    {"stage_id": "07A", "name": "character_lock", "output_file": "07A_character_lock.json"},
    {"stage_id": "07B", "name": "character_appearance", "output_file": "07B_character_appearance.json"},
    {"stage_id": "07C", "name": "reference_assets", "output_file": "07C_reference_assets.json"},
    {"stage_id": "07D", "name": "storyboard_frame", "output_file": "07D_storyboard_frame.json"},
    {"stage_id": "07E", "name": "finalize", "output_file": "07E_finalize.json"},
]
STAGE_BY_ID = {stage["stage_id"]: stage for stage in STAGES}


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_json(path: str | Path, data: dict[str, Any]) -> None:
    io_utils.ensure_dir(Path(path).parent)
    io_utils.write_json(path, data)


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _run_and_score(stage_id: str, data: dict[str, Any], output_dir: str | Path, output_file: str) -> dict[str, Any]:
    quality = quality_checker.evaluate_stage(stage_id, data)
    data["stage_quality"] = quality
    output_path = _write_stage(output_dir, output_file, data)
    status = "success" if quality["passed"] else "needs_review"
    stage = STAGE_BY_ID.get(stage_id, {"name": stage_id})
    stage_status_writer.mark_stage_finished(
        "07_storyboard_image",
        output_dir,
        stage_id,
        stage["name"],
        status,
        output_file=output_path,
        score=quality.get("score"),
        issues_count=len(quality.get("issues", []) or []),
    )
    return {"stage_id": stage_id, "status": status, "output_path": output_path, "quality": quality}


def _mark_started(stage_id: str, output_dir: str | Path) -> None:
    stage = STAGE_BY_ID.get(stage_id, {"name": stage_id})
    stage_status_writer.mark_stage_started("07_storyboard_image", output_dir, stage_id, stage["name"], "stage started")


def build_07e(
    plan: dict[str, Any],
    character_lock_manifest: dict[str, Any],
    appearance_manifest: dict[str, Any],
    reference_asset_manifest: dict[str, Any],
    image_manifest: dict[str, Any],
) -> dict[str, Any]:
    registry = image_registry.build_registry(character_lock_manifest, appearance_manifest, reference_asset_manifest, image_manifest)
    retry_plan = retry_manager.build_retry_plan(character_lock_manifest, appearance_manifest, reference_asset_manifest, image_manifest)
    missing: list[dict[str, Any]] = []
    for entry in registry.get("entries", []) or []:
        if isinstance(entry, dict) and not entry.get("image_path"):
            missing.append({"registry_key": entry.get("registry_key"), "category": entry.get("category"), "issue": "empty image_path"})
    dependency_index = plan.get("dependency_index", {})
    quality_report = {
        "needs_retry": retry_plan.get("needs_retry", False),
        "missing_images": missing,
        "retry_plan": retry_plan,
        "dependency_index_ready": bool(dependency_index),
        "note": "07E 只处理图片阶段局部重跑；除非 06 绑定断裂，否则不回滚 LLM 文本阶段。",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "07E_finalize",
        "status": "needs_retry" if retry_plan.get("needs_retry") or missing else "success",
        "asset_image_registry": registry,
        "dependency_index": dependency_index,
        "retry_plan": retry_plan,
        "quality_report": quality_report,
        "storyboard_image_meta": {
            "schema_version": SCHEMA_VERSION,
            "character_lock_count": len(character_lock_manifest.get("character_locks", []) or []),
            "appearance_count": len(appearance_manifest.get("appearances", []) or []),
            "scene_reference_count": len(reference_asset_manifest.get("scene_assets", []) or []),
            "prop_reference_count": len(reference_asset_manifest.get("prop_assets", []) or []),
            "storyboard_frame_count": len(image_manifest.get("images", []) or []),
            "needs_retry": retry_plan.get("needs_retry", False),
        },
    }


def run_image_stages(
    storyboard: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    if not storyboard or not storyboard.get("frames"):
        raise RuntimeError("07_storyboard_image requires 06_storyboard/storyboard.json with frames.")
    stage_status: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}

    _mark_started("07P", output_dir)
    outputs["07P"] = planner.build_plan(storyboard, characters, scenes, props)
    stage_status.append(_run_and_score("07P", outputs["07P"], output_dir, "07P_plan.json"))

    _mark_started("07A", output_dir)
    outputs["07A"] = phase_07a.run(outputs["07P"], characters, output_dir)
    stage_status.append(_run_and_score("07A", outputs["07A"], output_dir, "07A_character_lock.json"))
    _write_json(Path(output_dir) / "character_lock_manifest.json", outputs["07A"].get("character_lock_manifest", {}))

    _mark_started("07B", output_dir)
    outputs["07B"] = phase_07b.run(outputs["07P"], characters, outputs["07A"].get("character_lock_manifest", {}), output_dir)
    stage_status.append(_run_and_score("07B", outputs["07B"], output_dir, "07B_character_appearance.json"))
    _write_json(Path(output_dir) / "appearance_manifest.json", outputs["07B"].get("appearance_manifest", {}))

    _mark_started("07C", output_dir)
    outputs["07C"] = phase_07c.run(outputs["07P"], output_dir)
    stage_status.append(_run_and_score("07C", outputs["07C"], output_dir, "07C_reference_assets.json"))
    _write_json(Path(output_dir) / "reference_asset_manifest.json", outputs["07C"].get("reference_asset_manifest", {}))

    _mark_started("07D", output_dir)
    outputs["07D"] = phase_07d.run(
        outputs["07P"],
        storyboard,
        outputs["07B"].get("appearance_manifest", {}),
        outputs["07C"].get("reference_asset_manifest", {}),
        output_dir,
    )
    stage_status.append(_run_and_score("07D", outputs["07D"], output_dir, "07D_storyboard_frame.json"))
    _write_json(Path(output_dir) / "image_manifest.json", outputs["07D"].get("image_manifest", {}))

    _mark_started("07E", output_dir)
    outputs["07E"] = build_07e(
        outputs["07P"],
        outputs["07A"].get("character_lock_manifest", {}),
        outputs["07B"].get("appearance_manifest", {}),
        outputs["07C"].get("reference_asset_manifest", {}),
        outputs["07D"].get("image_manifest", {}),
    )
    stage_status.append(_run_and_score("07E", outputs["07E"], output_dir, "07E_finalize.json"))
    _write_json(Path(output_dir) / "dependency_index.json", outputs["07E"].get("dependency_index", {}))
    _write_json(Path(output_dir) / "asset_image_registry.json", outputs["07E"].get("asset_image_registry", {}))
    _write_json(Path(output_dir) / "storyboard_image_meta.json", outputs["07E"].get("storyboard_image_meta", {}))

    return {"schema_version": SCHEMA_VERSION, "stage_mode": "image_execution", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(
    storyboard: dict[str, Any],
    characters: dict[str, Any],
    scenes: dict[str, Any],
    props: dict[str, Any],
    config: dict[str, Any],
    stage_result: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    p = outputs["07P"]
    a = outputs["07A"]
    b = outputs["07B"]
    c = outputs["07C"]
    d = outputs["07D"]
    e = outputs["07E"]
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result.get("stage_status", [])}
    quality_report = e.get("quality_report", {}) if isinstance(e.get("quality_report"), dict) else {}
    image_manifest = d.get("image_manifest", {}) if isinstance(d.get("image_manifest"), dict) else {}
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "07_storyboard_image",
        "status": "success",
        "stage_mode": "image_execution",
        "execution_mode": "dry_run" if all((img.get("execution_mode") == "dry_run") for img in image_manifest.get("images", []) or []) else "execute",
        "stage_status": stage_result.get("stage_status", []),
        "source": {
            "required_upstream": ["06_storyboard.storyboard.json"],
            "optional_upstream": ["03_character_system.characters.json", "04_scene_system.scenes.json", "05_prop_system.props.json"],
            "upstream_schema_versions": {
                "03": characters.get("schema_version"),
                "04": scenes.get("schema_version"),
                "05": props.get("schema_version"),
                "06": storyboard.get("schema_version"),
            },
            "output_dir": str(output_dir),
        },
        "plan": p,
        "dependency_index": e.get("dependency_index", {}),
        "asset_image_registry": e.get("asset_image_registry", {}),
        "character_lock_manifest": a.get("character_lock_manifest", {}),
        "appearance_manifest": b.get("appearance_manifest", {}),
        "reference_asset_manifest": c.get("reference_asset_manifest", {}),
        "image_manifest": image_manifest,
        "images": image_manifest.get("images", []),
        "reference_asset_tasks": p.get("reference_asset_tasks", []),
        "frame_image_tasks": p.get("storyboard_frame_tasks", []),
        "execution_results": [img.get("execution_result", {}) for img in image_manifest.get("images", []) or [] if isinstance(img, dict)],
        "execution_summary": {
            "character_lock": a.get("execution_summary", {}),
            "character_appearance": b.get("execution_summary", {}),
            "reference_assets": c.get("execution_summary", {}),
            "storyboard_frame": d.get("execution_summary", {}),
        },
        "retry_plan": e.get("retry_plan", {}),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": [
            "07 已拆为 07P/07A/07B/07C/07D/07E：计划依赖图、定妆图、换装造型图、场景/道具参考图、正式分镜图、汇总总检。",
            "默认 dry_run 只生成任务、manifest 和预期图片路径；execute 模式需配置 workflow mapping 或全局 ComfyUI workflow。",
            "07 是 IMAGE_PHASE，入口释放 LLM 资源；07 内部不频繁卸载图片模型。",
        ],
        "config": config,
    }
    validation = schema_validator.validate_final_output({**data, "schema_validation": {}})
    needs_review = (
        any(item.get("status") != "success" for item in stage_result.get("stage_status", []))
        or bool(quality_report.get("needs_retry"))
        or not validation["passed"]
    )
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
