from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
script_adapter = import_module("08_audio.core.script_adapter")
indextts_client = import_module("08_audio.core.indextts_client")
wav_utils = import_module("08_audio.core.wav_utils")
quality_checker = import_module("08_audio.core.quality_checker")
schema_validator = import_module("08_audio.core.schema_validator")

SCHEMA_VERSION = "1.0"

STAGES: list[dict[str, str]] = [
    {"stage_id": "08A", "name": "audio_queue_build", "output_file": "08A_audio_queue.json"},
    {"stage_id": "08B", "name": "tts_segment_plan", "output_file": "08B_tts_segment_plan.json"},
    {"stage_id": "08C", "name": "tts_execution", "output_file": "08C_tts_execution.json"},
    {"stage_id": "08D", "name": "final_mix", "output_file": "08D_final_mix.json"},
]


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _run_and_score(stage_id: str, data: dict[str, Any], output_dir: str | Path, output_file: str) -> dict[str, Any]:
    quality = quality_checker.evaluate_stage(stage_id, data)
    data["stage_quality"] = quality
    output_path = _write_stage(output_dir, output_file, data)
    return {"stage_id": stage_id, "status": "success" if quality["passed"] else "needs_review", "output_path": output_path, "quality": quality}


def build_08d(execution: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    final_path = output_dir / "final_audio.wav"
    concat_paths: list[str] = []
    successful_segments: list[dict[str, Any]] = []
    for seg in execution.get("segments", []) or []:
        if not isinstance(seg, dict) or seg.get("status") != "success":
            continue
        concat_paths.append(str(seg.get("output_path")))
        if seg.get("pause_path"):
            concat_paths.append(str(seg.get("pause_path")))
        successful_segments.append(seg)

    duration = wav_utils.concat_wavs(concat_paths, final_path)
    return {
        "stage": "08D_final_mix",
        "status": "success" if successful_segments else "needs_review",
        "final_audio_path": str(final_path),
        "duration_seconds": duration,
        "segment_count": len(successful_segments),
        "failed_segments": execution.get("failed_segments", []),
        "mix_strategy": {
            "type": "linear_concat",
            "pause_after_line": True,
            "sample_policy": "first_segment_params_or_24k_mono_dry_run",
        },
        "notes": [
            "08D 当前做线性拼接，先保证音频驱动视频流程闭环。",
            "后续可扩展 BGM、音效、响度归一化、角色多音色与字幕时间轴。",
        ],
    }


def run_audio_stages(script: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    stage_status: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}

    outputs["08A"] = script_adapter.build_voice_queue(script)
    stage_status.append(_run_and_score("08A", outputs["08A"], output_dir, "08A_audio_queue.json"))

    outputs["08B"] = indextts_client.build_segment_plan(outputs["08A"].get("voice_queue", []), output_dir)
    stage_status.append(_run_and_score("08B", outputs["08B"], output_dir, "08B_tts_segment_plan.json"))

    outputs["08C"] = indextts_client.synthesize_segments(outputs["08B"], output_dir)
    stage_status.append(_run_and_score("08C", outputs["08C"], output_dir, "08C_tts_execution.json"))

    outputs["08D"] = build_08d(outputs["08C"], output_dir)
    stage_status.append(_run_and_score("08D", outputs["08D"], output_dir, "08D_final_mix.json"))

    return {"schema_version": SCHEMA_VERSION, "stage_mode": "audio_execution", "stage_status": stage_status, "outputs": outputs}


def merge_stage_outputs(script: dict[str, Any], config: dict[str, Any], stage_result: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    outputs = stage_result["outputs"]
    a = outputs["08A"]
    b = outputs["08B"]
    c = outputs["08C"]
    d = outputs["08D"]
    stage_scores = {item["stage_id"]: (item.get("quality") or {}).get("score") for item in stage_result.get("stage_status", [])}
    failed_segments = c.get("failed_segments", []) if isinstance(c.get("failed_segments"), list) else []

    data = {
        "schema_version": SCHEMA_VERSION,
        "module": "08_audio",
        "status": "success",
        "stage_mode": "audio_execution",
        "execution_mode": b.get("execution_mode"),
        "source": {
            "required_upstream": ["02_script_writer.script.json"],
            "upstream_schema_versions": {"02": script.get("schema_version")},
            "output_dir": str(output_dir),
        },
        "environment": b.get("environment", {}),
        "voice_queue": a.get("voice_queue", []),
        "segment_plan": b.get("segments", []),
        "segments": c.get("segments", []),
        "failed_segments": failed_segments,
        "final_audio_path": d.get("final_audio_path"),
        "duration_seconds": d.get("duration_seconds"),
        "mix_strategy": d.get("mix_strategy", {}),
        "stage_status": stage_result.get("stage_status", []),
        "quality_report": {
            "needs_retry": bool(failed_segments) or any(item.get("status") != "success" for item in stage_result.get("stage_status", [])),
            "retry_plan": {
                "retry_scope": "failed_audio_segments_only" if failed_segments else "none",
                "failed_segment_ids": [item.get("segment_id") for item in failed_segments if isinstance(item, dict)],
                "do_not_rerun_02": True,
            },
            "stage_scores": stage_scores,
        },
        "notes": [
            "08 是 AUDIO_PHASE，进入 09 前由总控释放音频模型资源。",
            "默认 dry_run 输出真实 WAV 静音文件，保证 09_video 依赖可检查。",
            "execute 模式调用本地根目录 index-tts，需 AI_DRAMA_AUDIO_EXECUTION_MODE=execute。",
        ],
        "config": config,
    }
    validation = schema_validator.validate_final_output({**data, "schema_validation": {}})
    needs_review = data["quality_report"]["needs_retry"] or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
