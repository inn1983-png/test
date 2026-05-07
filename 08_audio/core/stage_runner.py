from __future__ import annotations

from pathlib import Path
from typing import Any
from importlib import import_module

io_utils = import_module("00_common.io_utils")
stage_status_writer = import_module("00_common.stage_status")
script_adapter = import_module("08_audio.core.script_adapter")
voice_library = import_module("08_audio.core.voice_library")
emotion_mapper = import_module("08_audio.core.emotion_mapper")
indextts_client = import_module("08_audio.core.indextts_client")
wav_utils = import_module("08_audio.core.wav_utils")
timeline_builder = import_module("08_audio.core.timeline_builder")
audio_postprocess = import_module("08_audio.core.audio_postprocess")
quality_checker = import_module("08_audio.core.quality_checker")
schema_validator = import_module("08_audio.core.schema_validator")

SCHEMA_VERSION = "1.1"
LONG_VOICE_LINE_WARNING_SECONDS = 8.0
LONG_VOICE_LINE_REVIEW_SECONDS = 12.0

STAGES: list[dict[str, str]] = [
    {"stage_id": "08A", "name": "audio_queue_build", "output_file": "08A_audio_queue.json"},
    {"stage_id": "08B", "name": "voice_emotion_binding_and_tts_plan", "output_file": "08B_tts_segment_plan.json"},
    {"stage_id": "08C", "name": "tts_execution", "output_file": "08C_tts_execution.json"},
    {"stage_id": "08D", "name": "final_mix_timeline_subtitle", "output_file": "08D_final_mix.json"},
]
STAGE_BY_ID = {stage["stage_id"]: stage for stage in STAGES}


def _intermediate_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir) / "intermediate"
    io_utils.ensure_dir(path)
    return path


def _write_stage(output_dir: str | Path, filename: str, data: dict[str, Any]) -> str:
    path = _intermediate_dir(output_dir) / filename
    io_utils.write_json(path, data)
    return str(path)


def _write_text(path: str | Path, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _run_and_score(stage_id: str, data: dict[str, Any], output_dir: str | Path, output_file: str) -> dict[str, Any]:
    quality = quality_checker.evaluate_stage(stage_id, data)
    data["stage_quality"] = quality
    output_path = _write_stage(output_dir, output_file, data)
    status = "success" if quality["passed"] else "needs_review"
    stage = STAGE_BY_ID.get(stage_id, {"name": stage_id})
    stage_status_writer.mark_stage_finished(
        "08_audio",
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
    stage_status_writer.mark_stage_started("08_audio", output_dir, stage_id, stage["name"], "stage started")


def _is_silence_line(item: dict[str, Any]) -> bool:
    return str(item.get("line_type") or item.get("type") or "").upper() in {"S", "SILENCE", "留白"}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _entry_duration(entry: dict[str, Any]) -> float:
    duration = _safe_float(entry.get("duration_seconds") or entry.get("duration_sec") or entry.get("duration"), 0.0)
    if duration > 0:
        return duration
    start = _safe_float(entry.get("start_time") or entry.get("start_seconds") or entry.get("start"), 0.0)
    end = _safe_float(entry.get("end_time") or entry.get("end_seconds") or entry.get("end"), start)
    return max(0.0, end - start)


def _suggest_split(text: str) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    parts: list[str] = []
    current = ""
    for char in clean:
        current += char
        if char in "。！？!?；;，,":
            piece = current.strip()
            if piece:
                parts.append(piece)
            current = ""
    if current.strip():
        parts.append(current.strip())
    if len(parts) >= 2:
        return parts
    target = max(12, len(clean) // 2)
    return [clean[i : i + target] for i in range(0, len(clean), target)]


def build_audio_timing_review(timeline: dict[str, Any]) -> dict[str, Any]:
    entries = timeline.get("entries") if isinstance(timeline.get("entries"), list) else []
    long_lines: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or _is_silence_line(entry):
            continue
        duration = round(_entry_duration(entry), 3)
        if duration <= LONG_VOICE_LINE_WARNING_SECONDS:
            continue
        needs_review = duration > LONG_VOICE_LINE_REVIEW_SECONDS
        row = {
            "line_id": entry.get("audio_line_id") or entry.get("voice_line_id") or entry.get("line_id") or entry.get("segment_id") or f"audio_line_{index:04d}",
            "segment_id": entry.get("segment_id"),
            "speaker": entry.get("speaker"),
            "line_type": entry.get("line_type"),
            "text": entry.get("text") or "",
            "duration": duration,
            "issue_type": "voice_line_too_long" if needs_review else "voice_line_long_warning",
            "severity": "needs_review" if needs_review else "warning",
            "recommended_action": "return_to_02_split_sentence" if needs_review else "review_audio_pacing",
            "suggested_split": _suggest_split(str(entry.get("text") or "")),
        }
        long_lines.append(row)

    issues = [item for item in long_lines if item.get("severity") == "needs_review"]
    warnings = [item for item in long_lines if item.get("severity") == "warning"]
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "08_audio_timing_review",
        "status": "needs_review" if issues else ("warning" if warnings else "success"),
        "needs_review": bool(issues),
        "warning_count": len(warnings),
        "issue_count": len(issues),
        "total_duration_seconds": timeline.get("duration_seconds"),
        "voice_line_count": len([entry for entry in entries if isinstance(entry, dict) and not _is_silence_line(entry)]),
        "warning_threshold_seconds": LONG_VOICE_LINE_WARNING_SECONDS,
        "review_threshold_seconds": LONG_VOICE_LINE_REVIEW_SECONDS,
        "recommended_action": "return_to_02_split_sentence" if issues else ("review_audio_pacing" if warnings else "none"),
        "long_voice_lines": long_lines,
        "warnings": warnings,
        "issues": issues,
    }


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _entry_times(entry: dict[str, Any]) -> tuple[float, float, float]:
    start = _safe_float(entry.get("start_time") or entry.get("start_seconds") or entry.get("start"), 0.0)
    duration = _entry_duration(entry)
    end = _safe_float(entry.get("end_time") or entry.get("end_seconds") or entry.get("end"), start + duration)
    return round(start, 3), round(end, 3), round(duration, 3)


def _visual_role_for_entry(entry: dict[str, Any]) -> tuple[str, int, bool]:
    line_type = str(entry.get("line_type") or "").upper()
    text = str(entry.get("text") or "")
    emotion = str(entry.get("emotion") or "")
    combined = f"{text} {emotion}"
    start, end, duration = _entry_times(entry)
    _ = (start, end)
    location_keywords = ["来到", "院", "房", "屋", "街", "城", "山", "林", "雪地", "雨夜", "门外", "远处", "此时", "这时", "地点", "宫", "客栈"]
    prop_action_keywords = ["拿", "握", "攥", "推开", "打开", "拔", "刀", "剑", "枪", "信", "玉佩", "钥匙", "门", "杯", "药", "血", "破碎", "摔", "落下", "脚步"]
    emotional_burst_keywords = ["怒", "吼", "喊", "哭", "崩溃", "绝望", "震惊", "惊恐", "恐惧", "恨", "质问", "爆发", "发抖", "喘"]
    strong_dialogue = line_type in {"D", "DIALOGUE", "对白"} and ("！" in text or "!" in text or "？" in text or "?" in text or duration >= 5.5)
    emotional_burst = _has_any(combined, emotional_burst_keywords)
    if _is_silence_line(entry):
        return ("transition" if duration >= 2.0 else "empty_scene", 10, True)
    if line_type in {"OS", "M", "MONOLOGUE", "心理", "心理OS"}:
        return ("reaction" if emotional_burst else "closeup", 75 if emotional_burst else 55, duration >= 4.0)
    if emotional_burst:
        return ("closeup", 90, True)
    if _has_any(combined, prop_action_keywords):
        return ("insert", 65 if strong_dialogue else 45, duration >= 5.0)
    if line_type in {"N", "NARRATION", "旁白"} and _has_any(combined, location_keywords):
        return ("establishing", 35, duration >= 6.0)
    if strong_dialogue:
        return ("closeup", 70, duration >= 6.0)
    if line_type in {"D", "DIALOGUE", "对白"}:
        return ("closeup", 50, duration >= 6.0)
    if line_type in {"N", "NARRATION", "旁白"}:
        return ("establishing", 30, duration >= 7.0)
    return ("reaction", 40, duration >= 6.0)


def build_edit_rhythm(timeline: dict[str, Any]) -> dict[str, Any]:
    entries = timeline.get("entries") if isinstance(timeline.get("entries"), list) else []
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        start, end, duration = _entry_times(entry)
        role, intensity, needs_visual_pause = _visual_role_for_entry(entry)
        rows.append(
            {
                "segment_id": entry.get("segment_id") or f"audio_seg_{index:04d}",
                "audio_line_id": entry.get("audio_line_id"),
                "start": start,
                "end": end,
                "duration": duration,
                "line_type": entry.get("line_type"),
                "speaker": entry.get("speaker"),
                "text": entry.get("text") or "",
                "suggested_visual_role": role,
                "intensity": intensity,
                "needs_visual_pause": bool(needs_visual_pause),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "08_edit_rhythm",
        "status": "success",
        "total_duration_seconds": timeline.get("duration_seconds"),
        "segment_count": len(rows),
        "segments": rows,
        "rules": {
            "silence": "S -> empty_scene or transition",
            "os_monologue": "OS/M -> closeup or reaction",
            "strong_dialogue": "strong dialogue -> closeup",
            "location_narration": "location narration -> establishing",
            "prop_or_action": "prop/action description -> insert",
            "emotional_burst": "emotional burst -> closeup with high intensity",
        },
    }


def build_08b(queue_data: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    raw_queue = queue_data.get("voice_queue", []) if isinstance(queue_data.get("voice_queue"), list) else []
    emotion_queue = emotion_mapper.apply_emotion_mapping(raw_queue)
    binding = voice_library.bind_voices(emotion_queue, output_dir)
    plan = indextts_client.build_segment_plan(binding.get("voice_queue", []), output_dir)
    return {
        **plan,
        "stage": "08B_voice_emotion_binding_and_tts_plan",
        "voice_map": binding.get("voice_map", {}),
        "voice_binding_summary": binding.get("voice_binding_summary", {}),
        "voice_queue": binding.get("voice_queue", []),
        "notes": [
            "08B 先做角色音色绑定和情绪映射，再生成 TTS 分段计划。",
            "旁白 N 固定旁白音色；对白 D 绑定角色音色；心理 OS/M 绑定角色或 OS 音色；S 生成静音。",
        ],
    }


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
    timeline = timeline_builder.build_timeline(successful_segments, str(final_path), output_dir)
    timing_review = build_audio_timing_review(timeline)
    edit_rhythm = build_edit_rhythm(timeline)
    timeline_path = output_dir / "audio_timeline.json"
    timing_review_path = output_dir / "audio_timing_review.json"
    edit_rhythm_path = output_dir / "edit_rhythm.json"
    srt_path = output_dir / "subtitle.srt"
    ass_path = output_dir / "subtitle.ass"
    io_utils.write_json(timeline_path, timeline)
    io_utils.write_json(timing_review_path, timing_review)
    io_utils.write_json(edit_rhythm_path, edit_rhythm)
    _write_text(srt_path, timeline_builder.build_srt(timeline))
    _write_text(ass_path, timeline_builder.build_ass(timeline))
    postprocess = audio_postprocess.postprocess_audio(final_path, output_dir)
    return {
        "stage": "08D_final_mix_timeline_subtitle",
        "status": "needs_review" if not successful_segments or timing_review.get("needs_review") else "success",
        "final_audio_path": str(final_path),
        "duration_seconds": duration,
        "segment_count": len(successful_segments),
        "failed_segments": execution.get("failed_segments", []),
        "timeline_path": str(timeline_path),
        "audio_timing_review_path": str(timing_review_path),
        "audio_timing_review": timing_review,
        "edit_rhythm_path": str(edit_rhythm_path),
        "edit_rhythm": edit_rhythm,
        "subtitle_srt_path": str(srt_path),
        "subtitle_ass_path": str(ass_path),
        "timeline": timeline,
        "postprocess": postprocess,
        "mix_strategy": {
            "type": "linear_concat",
            "pause_after_line": True,
            "sample_policy": "first_segment_params_or_24k_mono_dry_run",
            "normalization": postprocess,
        },
        "notes": [
            "08D 输出 final_audio.wav、audio_timeline.json、subtitle.srt、subtitle.ass。",
            "后处理默认不破坏 final_audio.wav；开启 AI_DRAMA_AUDIO_NORMALIZE=1 时额外生成 final_audio_normalized.wav。",
        ],
    }


def run_audio_stages(script: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    stage_status: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}

    _mark_started("08A", output_dir)
    outputs["08A"] = script_adapter.build_voice_queue(script)
    stage_status.append(_run_and_score("08A", outputs["08A"], output_dir, "08A_audio_queue.json"))

    _mark_started("08B", output_dir)
    outputs["08B"] = build_08b(outputs["08A"], output_dir)
    stage_status.append(_run_and_score("08B", outputs["08B"], output_dir, "08B_tts_segment_plan.json"))

    _mark_started("08C", output_dir)
    outputs["08C"] = indextts_client.synthesize_segments(outputs["08B"], output_dir)
    stage_status.append(_run_and_score("08C", outputs["08C"], output_dir, "08C_tts_execution.json"))

    _mark_started("08D", output_dir)
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
    timing_review = d.get("audio_timing_review", {}) if isinstance(d.get("audio_timing_review"), dict) else {}
    edit_rhythm = d.get("edit_rhythm", {}) if isinstance(d.get("edit_rhythm"), dict) else {}

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
        "voice_map": b.get("voice_map", {}),
        "voice_binding_summary": b.get("voice_binding_summary", {}),
        "voice_queue": b.get("voice_queue", a.get("voice_queue", [])),
        "segment_plan": b.get("segments", []),
        "segments": c.get("segments", []),
        "failed_segments": failed_segments,
        "final_audio_path": d.get("final_audio_path"),
        "duration_seconds": d.get("duration_seconds"),
        "timeline_path": d.get("timeline_path"),
        "audio_timing_review_path": d.get("audio_timing_review_path"),
        "audio_timing_review": timing_review,
        "edit_rhythm_path": d.get("edit_rhythm_path"),
        "edit_rhythm": edit_rhythm,
        "subtitle_srt_path": d.get("subtitle_srt_path"),
        "subtitle_ass_path": d.get("subtitle_ass_path"),
        "audio_timeline": d.get("timeline", {}),
        "postprocess": d.get("postprocess", {}),
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
            "audio_timing_needs_review": bool(timing_review.get("needs_review")),
            "long_voice_line_count": len(timing_review.get("long_voice_lines", []) or []),
            "edit_rhythm_segment_count": len(edit_rhythm.get("segments", []) or []),
            "recommended_audio_action": timing_review.get("recommended_action"),
        },
        "notes": [
            "08 是 AUDIO_PHASE，进入 09 前由总控释放音频模型资源。",
            "默认 dry_run 输出真实 WAV 静音文件，保证 09_video 依赖可检查。",
            "execute 模式调用本地根目录 index-tts，需 AI_DRAMA_AUDIO_EXECUTION_MODE=execute。",
            "08 已吸收 TxtovideoAudio 的 N/D/M/S 思路：从真实音频时长出发，为 09 的 6-12 秒视频单元规划服务。",
        ],
        "config": config,
    }
    validation = schema_validator.validate_final_output({**data, "schema_validation": {}})
    needs_review = data["quality_report"]["needs_retry"] or not validation["passed"]
    data["schema_validation"] = validation
    data["quality_report"] = {**data["quality_report"], "needs_review": needs_review, "schema_validation_passed": validation["passed"], "schema_validation_issues": validation["issues"]}
    data["status"] = "needs_review" if needs_review else "success"
    return data
