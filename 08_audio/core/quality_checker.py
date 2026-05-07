from __future__ import annotations

from typing import Any


def _is_silence(item: dict[str, Any]) -> bool:
    return str(item.get("line_type") or "").upper() in {"S", "SILENCE", "留白"}


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    score = 100

    if stage_id == "08A":
        lines = data.get("voice_queue", [])
        if not isinstance(lines, list) or not lines:
            issues.append("08A 未能从 02_script_writer/script.json 提取任何可配音文本。")
            score -= 70
        for line in lines if isinstance(lines, list) else []:
            if not isinstance(line, dict):
                issues.append("08A 存在非法音频行。")
                score -= 10
                break
            if not _is_silence(line) and not line.get("text"):
                issues.append("08A 存在空文本音频行。")
                score -= 10
                break

    elif stage_id == "08B":
        segments = data.get("segments", [])
        env = data.get("environment", {}) if isinstance(data.get("environment"), dict) else {}
        binding = data.get("voice_binding_summary", {}) if isinstance(data.get("voice_binding_summary"), dict) else {}
        if not isinstance(segments, list) or not segments:
            issues.append("08B 没有生成 TTS 分段计划。")
            score -= 60
        fallback_count = int(binding.get("fallback_count") or 0)
        if fallback_count:
            issues.append(f"08B 有 {fallback_count} 条音频行使用 fallback 音色。")
            score -= min(25, fallback_count * 5)
        for seg in segments if isinstance(segments, list) else []:
            if isinstance(seg, dict) and not _is_silence(seg) and not seg.get("spk_audio_prompt"):
                issues.append("08B 存在未绑定 spk_audio_prompt 的非静音分段。")
                score -= 30
                break
        if data.get("execution_mode") == "execute":
            for key in ("root_exists", "checkpoints_exists", "config_yaml_exists", "uv_available"):
                if not env.get(key):
                    issues.append(f"execute 模式环境未就绪：{key}=false。")
                    score -= 8
        long_text_count = 0
        for seg in segments if isinstance(segments, list) else []:
            if not isinstance(seg, dict) or _is_silence(seg):
                continue
            text = str(seg.get("text") or "")
            if len(text) > 150:
                long_text_count += 1
        if long_text_count:
            warnings.append(f"08B 有 {long_text_count} 条文本超过 150 字符，TTS 可能截断或质量下降，建议回到 02 拆句。")
            score -= min(15, long_text_count * 5)

    elif stage_id == "08C":
        summary = data.get("execution_summary", {}) if isinstance(data.get("execution_summary"), dict) else {}
        failed = int(summary.get("failed") or 0)
        if failed:
            issues.append(f"08C 有 {failed} 个音频段生成失败。")
            score -= min(80, failed * 20)

    elif stage_id == "08D":
        if not data.get("final_audio_path"):
            issues.append("08D 缺少 final_audio_path。")
            score -= 60
        if float(data.get("duration_seconds") or 0) <= 0:
            issues.append("08D final_audio.wav 时长无效。")
            score -= 40
        for key in ("timeline_path", "subtitle_srt_path", "subtitle_ass_path"):
            if not data.get(key):
                issues.append(f"08D 缺少 {key}。")
                score -= 10
        if not data.get("audio_timing_review_path"):
            issues.append("08D 缺少 audio_timing_review_path。")
            score -= 15
        if not data.get("edit_rhythm_path"):
            issues.append("08D 缺少 edit_rhythm_path。")
            score -= 15
        timeline = data.get("timeline", {}) if isinstance(data.get("timeline"), dict) else {}
        if not timeline.get("entries"):
            issues.append("08D audio_timeline 没有 entries。")
            score -= 20
        edit_rhythm = data.get("edit_rhythm", {}) if isinstance(data.get("edit_rhythm"), dict) else {}
        if timeline.get("entries") and len(edit_rhythm.get("segments", []) or []) != len(timeline.get("entries", []) or []):
            issues.append("08D edit_rhythm 段数必须和 audio_timeline.entries 对齐。")
            score -= 20
        timing_review = data.get("audio_timing_review", {}) if isinstance(data.get("audio_timing_review"), dict) else {}
        warning_count = int(timing_review.get("warning_count") or 0)
        issue_count = int(timing_review.get("issue_count") or 0)
        if warning_count:
            warnings.append(f"08D 有 {warning_count} 条非静音 voice_line 超过 8 秒，建议检查节奏。")
            score -= min(10, warning_count * 2)
        if issue_count or timing_review.get("needs_review"):
            issues.append(f"08D 有 {issue_count} 条非静音 voice_line 超过 12 秒，需要回到 02 拆句。")
            score -= min(60, max(1, issue_count) * 30)

    score = max(0, min(100, score))
    return {
        "score": score,
        "passed": score >= 80 and not issues,
        "issues": issues,
        "warnings": warnings,
        "revision_instructions": [
            "检查 02_script_writer/script.json 是否包含 voice_lines/audio_lines/segments，或是否使用【N/D/M/S】标记。",
            "检查 shared_assets/voice_library/voices.json 或 AI_DRAMA_VOICE_MAP 是否覆盖主要角色音色。",
            "execute 模式下确认根目录 index-tts 存在、checkpoints/config.yaml 存在、角色音色样本存在，并已安装 uv。",
            "如果 audio_timing_review.json 中存在 voice_line_too_long，优先回到 02_script_writer 拆句，再重新生成 08。",
        ] if issues else [],
    }
