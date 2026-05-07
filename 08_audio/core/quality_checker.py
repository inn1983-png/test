from __future__ import annotations

from typing import Any


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100

    if stage_id == "08A":
        lines = data.get("voice_queue", [])
        if not isinstance(lines, list) or not lines:
            issues.append("08A 未能从 02_script_writer/script.json 提取任何可配音文本。")
            score -= 70
        for line in lines if isinstance(lines, list) else []:
            if not isinstance(line, dict) or not line.get("text"):
                issues.append("08A 存在空文本音频行。")
                score -= 10
                break

    elif stage_id == "08B":
        segments = data.get("segments", [])
        env = data.get("environment", {}) if isinstance(data.get("environment"), dict) else {}
        if not isinstance(segments, list) or not segments:
            issues.append("08B 没有生成 TTS 分段计划。")
            score -= 60
        if data.get("execution_mode") == "execute":
            for key in ("root_exists", "checkpoints_exists", "config_yaml_exists", "default_voice_prompt_exists", "uv_available"):
                if not env.get(key):
                    issues.append(f"execute 模式环境未就绪：{key}=false。")
                    score -= 8

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

    score = max(0, min(100, score))
    return {
        "score": score,
        "passed": score >= 80 and not issues,
        "issues": issues,
        "revision_instructions": [
            "检查 02_script_writer/script.json 是否包含 voice_lines/audio_lines/segments 等可提取文本。",
            "execute 模式下确认根目录 index-tts 存在、checkpoints/config.yaml 存在、默认音色样本存在，并已安装 uv。",
        ] if issues else [],
    }
