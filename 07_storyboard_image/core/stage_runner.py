from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
quality_checker = import_module("07_storyboard_image.core.quality_checker")
schema_validator = import_module("07_storyboard_image.core.schema_validator")
comfyui_client_module = import_module("07_storyboard_image.core.comfyui_client")

SCHEMA_VERSION = "1.0"

STAGES: list[dict[str, str]] = [
    {"stage_id": "07A", "name": "reference_asset_prepare", "output_file": "07A_reference_asset_prepare.json"},
    {"stage_id": "07B", "name": "frame_image_task_build", "output_file": "07B_frame_image_tasks.json"},
    {"stage_id": "07C", "name": "comfyui_execution", "output_file": "07C_comfyui_execution.json"},
    {"stage_id": "07D", "name": "manifest_quality_check", "output_file": "07D_manifest_quality_check.json"},
]


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _asset_image_base() -> str:
    return os.getenv("AI_DRAMA_ASSET_IMAGE_BASE", "shared_assets").rstrip("/")


def _safe_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value.strip()) or "asset"


def _scene_name(frame: dict[str, Any]) -> str:
    scene = frame.get("scene")
    if isinstance(scene, dict):
        return str(scene.get("canonical_scene_name", ""))
    return str(scene or "")


def _prop_name(prop: Any) -> str:
    if isinstance(prop, dict):
        return str(prop.get("canonical_prop_name", ""))
    return str(prop or "")


def _reference_path(kind: str, key: str) -> str:
    base = _asset_image_base()
    return f"{base}/{kind}/{_safe_key(key)}.png"


def _collect_reference_asset_tasks(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for req in storyboard.get("appearance_asset_requirements", []) or []:
        if not isinstance(req, dict):
            continue
        asset_key = str(req.get("appearance_asset_key", "")).strip()
        canonical_name = str(req.get("canonical_name", "")).strip()
        if not asset_key:
            continue
        tasks[f"appearance:{asset_key}"] = {
            "task_id": f"ref_appearance_{_safe_key(asset_key)}",
            "asset_kind": "character_appearance",
            "asset_key": asset_key,
            "canonical_name": canonical_name,
            "generation_stage": "lock_face_then_costume_variant",
            "source_reference": req,
            "expected_image_path": _reference_path("characters/appearance", asset_key),
        }
    for frame in storyboard.get("frames", []) or []:
        if not isinstance(frame, dict):
            continue
        scene_name = _scene_name(frame)
        if scene_name:
            tasks.setdefault(f"scene:{scene_name}", {
                "task_id": f"ref_scene_{_safe_key(scene_name)}",
                "asset_kind": "scene",
                "asset_key": scene_name,
                "generation_stage": "scene_reference_image",
                "source_reference": frame.get("scene", {}),
                "expected_image_path": _reference_path("scenes", scene_name),
            })
        for prop in frame.get("props", []) or []:
            prop_name = _prop_name(prop)
            if prop_name:
                tasks.setdefault(f"prop:{prop_name}", {
                    "task_id": f"ref_prop_{_safe_key(prop_name)}",
                    "asset_kind": "prop",
                    "asset_key": prop_name,
                    "generation_stage": "prop_reference_image",
                    "source_reference": prop,
                    "expected_image_path": _reference_path("props", prop_name),
                })
    return list(tasks.values())


def _missing_reference_report(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    strict = os.getenv("AI_DRAMA_REQUIRE_REFERENCE_IMAGES", "0").strip().lower() in {"1", "true", "yes", "on"}
    for task in tasks:
        path = str(task.get("expected_image_path", ""))
        if strict and path and not Path(path).exists():
            missing.append({
                "task_id": task.get("task_id"),
                "asset_kind": task.get("asset_kind"),
                "asset_key": task.get("asset_key"),
                "expected_image_path": path,
                "issue": "reference image file not found",
            })
    return missing


def build_07a(storyboard: dict[str, Any]) -> dict[str, Any]:
    tasks = _collect_reference_asset_tasks(storyboard)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "reference_asset_prepare",
        "status": "prepared",
        "reference_asset_tasks": tasks,
        "missing_references": _missing_reference_report(tasks),
        "asset_generation_policy": {
            "character_order": "fixed_face_reference -> costume_or_wearable_appearance_reference -> final_frame_image",
            "scene_order": "scene_reference_before_frame",
            "prop_order": "independent_prop_reference_when_visible_or_story_critical",
            "note": "07 可以生成或引用参考图；06 不生成图片提示词，07 才把分镜语义转为图片执行任务。",
        },
    }


def _style_suffix() -> str:
    return os.getenv(
        "AI_DRAMA_IMAGE_STYLE_SUFFIX",
        "Chinese historical drama, cinematic realistic live-action style, natural color, ancient China setting, consistent characters, stable scene, high detail, no modern objects",
    )


def _negative_prompt() -> str:
    return os.getenv(
        "AI_DRAMA_IMAGE_NEGATIVE_PROMPT",
        "modern objects, modern clothing, western face, cartoon, anime, 3d render, low quality, blurry, extra limbs, deformed hands, wrong gender, duplicate people, text, watermark",
    )


def _character_prompt_parts(frame: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for char in frame.get("characters", []) or []:
        if not isinstance(char, dict):
            continue
        name = str(char.get("canonical_name", "")).strip()
        costume_id = str(char.get("costume_id", "")).strip()
        appearance_key = str(char.get("appearance_asset_key", "")).strip()
        lock_ref = str(char.get("character_lock_reference", "")).strip()
        wearable = ", ".join(map(str, char.get("wearable_props", []) or []))
        parts.append(f"角色:{name}; 服装:{costume_id}; 造型引用:{appearance_key}; 锁脸:{lock_ref}; 穿戴物:{wearable}")
    return parts


def _reference_images_for_frame(frame: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    scene_name = _scene_name(frame)
    if scene_name:
        refs.append({"kind": "scene", "key": scene_name, "path": _reference_path("scenes", scene_name), "required": True})
    for char in frame.get("characters", []) or []:
        if isinstance(char, dict) and char.get("appearance_asset_key"):
            key = str(char["appearance_asset_key"])
            refs.append({"kind": "character_appearance", "key": key, "path": _reference_path("characters/appearance", key), "required": True})
    for prop in frame.get("props", []) or []:
        prop_name = _prop_name(prop)
        if prop_name:
            refs.append({"kind": "prop", "key": prop_name, "path": _reference_path("props", prop_name), "required": False})
    return refs


def build_frame_task(frame: dict[str, Any]) -> dict[str, Any]:
    frame_id = str(frame.get("frame_id", "frame"))
    seq = frame.get("sequence_index", 0)
    scene_name = _scene_name(frame)
    char_parts = _character_prompt_parts(frame)
    prop_parts = [_prop_name(prop) for prop in frame.get("props", []) or [] if _prop_name(prop)]
    camera = frame.get("camera_plan", {})
    positive_parts = [
        f"单帧分镜 {frame_id}",
        f"场景:{scene_name}",
        f"人物:{' | '.join(char_parts) if char_parts else '无主要人物'}",
        f"道具:{', '.join(prop_parts) if prop_parts else '无关键道具'}",
        f"剧情动作:{frame.get('story_action', '')}",
        f"情绪:{frame.get('emotion', '')}",
        f"镜头:{camera}",
        f"构图:{frame.get('composition_notes', '')}",
        f"连续性:{frame.get('continuity_notes', '')}",
        _style_suffix(),
    ]
    return {
        "task_id": f"img_{_safe_key(frame_id)}",
        "frame_id": frame_id,
        "sequence_index": seq,
        "source_frame": frame,
        "scene": frame.get("scene", {}),
        "characters": frame.get("characters", []),
        "props": frame.get("props", []),
        "positive_prompt": "\n".join(str(part) for part in positive_parts if str(part).strip()),
        "negative_prompt": _negative_prompt(),
        "reference_images": _reference_images_for_frame(frame),
        "output_basename": f"shot_{int(seq):03d}" if isinstance(seq, int) and seq > 0 else _safe_key(frame_id),
    }


def build_07b(storyboard: dict[str, Any]) -> dict[str, Any]:
    frames = storyboard.get("frames", []) or []
    tasks = [build_frame_task(frame) for frame in frames if isinstance(frame, dict)]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "frame_image_task_build",
        "status": "prepared",
        "frame_image_tasks": tasks,
        "prompt_style_policy": {
            "source": "07 deterministic prompt builder from 06 reference_requirements/composition_notes/continuity_notes",
            "style_suffix_env": "AI_DRAMA_IMAGE_STYLE_SUFFIX",
            "rule": "同一 frame 的人物、场景、道具只能来自 06 已绑定资产引用。",
        },
        "negative_prompt_policy": {
            "negative_prompt_env": "AI_DRAMA_IMAGE_NEGATIVE_PROMPT",
            "default_focus": "屏蔽现代物、欧美脸、卡通、3D、低质量、性别错误、多人污染。",
        },
    }


def build_07c(frame_tasks: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    client = comfyui_client_module.ComfyUIClient()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for task in frame_tasks:
        try:
            result = client.submit_task(task, output_dir)
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            failure = {
                "frame_id": task.get("frame_id"),
                "status": "failed",
                "execution_mode": client.mode,
                "output_path": "",
                "error": str(exc),
            }
            results.append(failure)
            failures.append(failure)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "comfyui_execution",
        "status": "success" if not failures else "needs_retry",
        "execution_mode": "dry_run" if client.dry_run else "execute",
        "execution_results": results,
        "execution_summary": {
            "total": len(frame_tasks),
            "success_or_planned": len([r for r in results if r.get("status") in {"planned", "submitted", "success"}]),
            "failed": len(failures),
            "failures": failures,
        },
    }


def build_07d(storyboard: dict[str, Any], tasks: list[dict[str, Any]], execution: dict[str, Any]) -> dict[str, Any]:
    results_by_frame = {str(item.get("frame_id")): item for item in execution.get("execution_results", []) if isinstance(item, dict)}
    images: list[dict[str, Any]] = []
    for task in tasks:
        frame_id = str(task.get("frame_id"))
        result = results_by_frame.get(frame_id, {})
        images.append({
            "frame_id": frame_id,
            "sequence_index": task.get("sequence_index"),
            "source_frame_id": frame_id,
            "image_path": result.get("output_path", ""),
            "status": result.get("status", "unknown"),
            "execution_mode": result.get("execution_mode", execution.get("execution_mode", "dry_run")),
            "scene": task.get("scene", {}),
            "characters": task.get("characters", []),
            "props": task.get("props", []),
            "reference_images": task.get("reference_images", []),
            "prompt_summary": {
                "positive_prompt_chars": len(str(task.get("positive_prompt", ""))),
                "negative_prompt_chars": len(str(task.get("negative_prompt", ""))),
                "output_basename": task.get("output_basename"),
            },
        })
    failed_frames = [img["frame_id"] for img in images if img.get("status") == "failed"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "images": images,
        "source_storyboard_module": storyboard.get("module", "06_storyboard"),
        "source_storyboard_schema_version": storyboard.get("schema_version"),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "manifest_quality_check",
        "status": "needs_retry" if failed_frames else "success",
        "image_manifest": manifest,
        "quality_report": {
            "needs_retry": bool(failed_frames),
            "retry_frames": failed_frames,
            "issues": [f"分镜图生成失败：{fid}" for fid in failed_frames],
            "note": "dry_run 模式下 status=planned 视为可通过；execute 模式下 failed 需要重跑对应帧。",
        },
        "retry_plan": {
            "retry_scope": "failed_frames_only" if failed_frames else "none",
            "retry_frames": failed_frames,
        },
    }


def _run_and_score(stage_id: str, data: dict[str, Any], output_dir: str | Path, output_file: str) -> dict[str, Any]:
    quality = quality_checker.evaluate_stage(stage_id, data)
    data["stage_quality"] = quality
    output_path = _write_stage(output_dir, output_file, data)
    return {"stage_id": stage_id, "status": "success" if quality["passed"] else "needs_review", "output_path": output_path, "quality": quality}


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

    outputs["07A"] = build_07a(storyboard)
    stage_status.append(_run_and_score("07A", outputs["07A"], output_dir, "07A_reference_asset_prepare.json"))

    outputs["07B"] = build_07b(storyboard)
    stage_status.append(_run_and_score("07B", outputs["07B"], output_dir, "07B_frame_image_tasks.json"))

    outputs["07C"] = build_07c(outputs["07B"].get("frame_image_tasks", []), output_dir)
    stage_status.append(_run_and_score("07C", outputs["07C"], output_dir, "07C_comfyui_execution.json"))

    outputs["07D"] = build_07d(storyboard, outputs["07B"].get("frame_image_tasks", []), outputs["07C"])
    stage_status.append(_run_and_score("07D", outputs["07D"], output_dir, "07D_manifest_quality_check.json"))

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
    a, b, c, d = outputs["07A"], outputs["07B"], outputs["07C"], outputs["07D"]
    images = d.get("image_manifest", {}).get("images", []) if isinstance(d.get("image_manifest"), dict) else []
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result.get("stage_status", [])}
    quality_report = d.get("quality_report", {}) if isinstance(d.get("quality_report"), dict) else {}
    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "07_storyboard_image",
        "status": "success",
        "stage_mode": "image_execution",
        "execution_mode": c.get("execution_mode", "dry_run"),
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
        "reference_asset_tasks": a.get("reference_asset_tasks", []),
        "asset_generation_policy": a.get("asset_generation_policy", {}),
        "missing_references": a.get("missing_references", []),
        "frame_image_tasks": b.get("frame_image_tasks", []),
        "prompt_style_policy": b.get("prompt_style_policy", {}),
        "negative_prompt_policy": b.get("negative_prompt_policy", {}),
        "execution_results": c.get("execution_results", []),
        "execution_summary": c.get("execution_summary", {}),
        "images": images,
        "image_manifest": d.get("image_manifest", {}),
        "retry_plan": d.get("retry_plan", {}),
        "quality_report": {**quality_report, "stage_scores": stage_scores},
        "notes": [
            "07 是图片执行阶段；默认 dry_run 只生成任务与 manifest，不真正调用 ComfyUI。",
            "设置 AI_DRAMA_IMAGE_EXECUTION_MODE=execute、AI_DRAMA_COMFYUI_WORKFLOW 和节点注入环境变量后，可提交 ComfyUI API workflow。",
            "07 会在入口处调用 release_llm_resources，作为 06->07 的模型族切换边界。",
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
