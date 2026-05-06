from __future__ import annotations

from typing import Any


STAGE_THRESHOLDS = {
    "02A": 88,
    "02B": 88,
    "02C": 90,
    "02D": 92,
    "02E": 90,
    "02F": 92,
}

REQUIRED_KEYS = {
    "02A": ["adaptation_blueprint", "coverage_plan", "tone_plan", "compression_guardrails", "length_strategy", "episode_split_plan", "script_version_strategy"],
    "02B": ["script_structure", "scene_beats", "event_coverage_map", "retention_design", "character_name_usage", "script_emotion_curve"],
    "02C": ["voice_line_plan", "script_video_unit_candidates", "duration_risk_report"],
    "02D": ["script", "segments", "script_text", "source_line_usage", "script_versions", "selected_version_id", "tts_readability_report"],
    "02E": ["production_annotations", "audio_cues", "visual_dramatic_units", "storyboard_hints", "risk_report", "visual_executability_report", "character_load_report", "continuity_chain"],
    "02F": ["quality_report", "evidence_index", "warnings", "revision_plan", "failure_learning_notes"],
}


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_KEYS.get(stage_id, []) if key not in data]
    score = 100 - len(missing) * 10
    issues: list[str] = []
    suggestions: list[str] = []

    if missing:
        issues.append(f"缺少必要字段：{', '.join(missing)}")
        suggestions.append("补齐缺失字段，并保持字段名与 02 schema 完全一致。")

    if data.get("status") == "scaffold":
        score = min(score, 50)
        issues.append("当前仍是 scaffold 占位输出。")
        suggestions.append("调用真实 LLM 生成本阶段内容，避免只返回占位文本。")

    if stage_id == "02A":
        score, issues, suggestions = _evaluate_blueprint(data, score, issues, suggestions)
    elif stage_id == "02B":
        score, issues, suggestions = _evaluate_structure(data, score, issues, suggestions)
    elif stage_id == "02C":
        score, issues, suggestions = _evaluate_voice_line_plan(data, score, issues, suggestions)
    elif stage_id == "02D":
        score, issues, suggestions = _evaluate_script(data, score, issues, suggestions)
    elif stage_id == "02E":
        score, issues, suggestions = _evaluate_annotations(data, score, issues, suggestions)
    elif stage_id == "02F":
        score, issues, suggestions = _evaluate_final_check(data, score, issues, suggestions)

    score = max(0, min(100, score))
    threshold = STAGE_THRESHOLDS.get(stage_id, 88)
    passed = score >= threshold and not missing

    return {
        "stage_id": stage_id,
        "score": score,
        "threshold": threshold,
        "passed": passed,
        "issues": issues,
        "revision_instructions": suggestions,
    }


def _evaluate_blueprint(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    plan = data.get("coverage_plan") or []
    if not isinstance(plan, list) or not plan:
        score -= 22
        issues.append("coverage_plan 为空，无法保证关键事件不遗漏。")
        suggestions.append("按 01 的 events / high_retention_segments 逐项列出改编覆盖计划。")
    guardrails = data.get("compression_guardrails") or {}
    if not guardrails:
        score -= 16
        issues.append("compression_guardrails 为空，容易把长文案压成过短剧本。")
        suggestions.append("明确不得过度压缩、不得把多个关键事件合并成一句话的规则。")
    length_strategy = data.get("length_strategy") or {}
    if not length_strategy:
        score -= 18
        issues.append("length_strategy 为空，无法控制长文案不要被压成固定 2 分钟。")
        suggestions.append("补充 adaptation_mode、minimum_scene_beat_count、minimum_voice_line_count、allow_multi_episode_split。")
    episode_plan = data.get("episode_split_plan") or []
    if not isinstance(episode_plan, list) or not episode_plan:
        score -= 12
        issues.append("episode_split_plan 为空，长篇章节无法判断是否需要拆集/拆段。")
        suggestions.append("按故事容量输出 episode_split_plan，即使只有一集也要说明。")
    version_strategy = data.get("script_version_strategy") or {}
    if not isinstance(version_strategy, dict) or not version_strategy:
        score -= 10
        issues.append("script_version_strategy 为空，后续无法做多版本剧本选择。")
        suggestions.append("说明后续 script_versions 应包含忠于原文、短剧刺激、音频驱动等版本策略。")
    return score, issues, suggestions


def _evaluate_structure(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    beats = data.get("scene_beats") or []
    if not isinstance(beats, list) or len(beats) < 3:
        score -= 25
        issues.append("scene_beats 数量过少，剧本结构可能压缩过狠。")
        suggestions.append("至少按开场压迫、冲突升级、转折/反杀、余韵拆成多个 beat。")
    coverage = data.get("event_coverage_map") or []
    if not isinstance(coverage, list) or not coverage:
        score -= 20
        issues.append("event_coverage_map 为空，无法验证事件覆盖。")
        suggestions.append("为每个使用到的 source_event_id 标记对应 scene_beat_id。")
    character_usage = data.get("character_name_usage") or []
    if not isinstance(character_usage, list) or not character_usage:
        score -= 12
        issues.append("character_name_usage 为空，后续角色一致性风险较高。")
        suggestions.append("列出 canonical_name、aliases_used、dialogue_speaker_names，禁止新造年龄前缀角色名。")
    curve = data.get("script_emotion_curve") or []
    if not isinstance(curve, list) or len(curve) < 3:
        score -= 12
        issues.append("script_emotion_curve 不完整，剧本情绪可能发平。")
        suggestions.append("至少输出 opening / midpoint / payoff / ending_hook 等情绪节点和强度。")
    return score, issues, suggestions


def _evaluate_voice_line_plan(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    voice_lines = data.get("voice_line_plan") or []
    if not isinstance(voice_lines, list) or not voice_lines:
        score -= 35
        issues.append("voice_line_plan 为空，08_audio 无法直接切配音。")
        suggestions.append("按 N/D/M/S 拆出语音行，每条尽量适合 6-12 秒视频单元。")
        return score, issues, suggestions

    allowed = {"N", "D", "M", "S"}
    has_speech = False
    for item in voice_lines:
        if not isinstance(item, dict):
            continue
        line_type = item.get("voice_line_type")
        if line_type not in allowed:
            score -= 8
            issues.append(f"存在非法 voice_line_type：{line_type}")
            suggestions.append("voice_line_type 只能是 N / D / M / S。")
            break
        if line_type in {"N", "D", "M"}:
            has_speech = True
            if not item.get("tts_text"):
                score -= 8
                issues.append("存在语音行缺少 tts_text。")
                suggestions.append("N/D/M 类型必须提供可直接送入 TTS 的 tts_text。")
                break
        duration = item.get("estimated_duration_sec")
        if isinstance(duration, (int, float)) and duration > 12:
            score -= 15
            issues.append("存在 estimated_duration_sec 超过 12 秒的语音行。")
            suggestions.append("拆短该语音行，或插入 S 留白，将单条语音控制在后续视频单元可承载范围内。")
            break
    if not has_speech:
        score -= 20
        issues.append("voice_line_plan 没有任何 N/D/M 语音行。")
        suggestions.append("必须生成旁白、对白或心理 OS，不能只有静音留白。")

    units = data.get("script_video_unit_candidates") or []
    if not isinstance(units, list) or not units:
        score -= 18
        issues.append("script_video_unit_candidates 为空，后续视频单元规划无法提前预判。")
        suggestions.append("按一个 voice_line + 一个主场景 + 一个连续动作链生成候选视频单元。")
    return score, issues, suggestions


def _evaluate_script(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    segments = data.get("segments") or []
    if not isinstance(segments, list) or not segments:
        score -= 35
        issues.append("segments 为空，未生成正式剧本段落。")
        suggestions.append("生成包含 OS、对白、动作、留白的 segments 数组。")
        return score, issues, suggestions

    versions = data.get("script_versions") or []
    if not isinstance(versions, list) or len(versions) < 2:
        score -= 12
        issues.append("script_versions 少于 2 个，无法比较忠于原文/短剧刺激/音频驱动等版本。")
        suggestions.append("至少输出两个剧本版本，并说明 selected_version_id 的选择理由。")
    if not data.get("selected_version_id"):
        score -= 8
        issues.append("selected_version_id 为空。")
        suggestions.append("从 script_versions 中选择一个最终版本并给出选择理由。")

    types = {str(item.get("type")) for item in segments if isinstance(item, dict)}
    if "os" not in types:
        score -= 12
        issues.append("剧本缺少 OS 段落。")
        suggestions.append("补充【OS】旁白/心理独白，用于承接信息和情绪。")
    if "dialogue" not in types:
        score -= 20
        issues.append("剧本缺少对白段落。")
        suggestions.append("补充角色对白，保留原文关键冲突、羞辱、逼问、反杀信息。")
    if "blank" not in types:
        score -= 10
        issues.append("剧本缺少留白段落。")
        suggestions.append("补充【留白】节奏停顿，给音频和画面呼吸空间。")

    for item in segments:
        if not isinstance(item, dict):
            continue
        if not item.get("segment_id"):
            score -= 8
            issues.append("存在 segment 缺少 segment_id。")
            suggestions.append("每个 segment 必须有稳定 segment_id。")
            break
        if not item.get("voice_line_id"):
            score -= 8
            issues.append("存在 segment 缺少 voice_line_id。")
            suggestions.append("每个 segment 必须绑定 02C 的 voice_line_id，方便音频和视频单元继续使用。")
            break
        if item.get("type") == "dialogue" and not item.get("speaker"):
            score -= 8
            issues.append("存在 dialogue segment 缺少 speaker。")
            suggestions.append("对白段必须使用稳定角色名作为 speaker。")
            break
    if not data.get("source_line_usage"):
        score -= 12
        issues.append("source_line_usage 为空，无法确认原文关键句是否继承。")
        suggestions.append("列出 01 golden_lines / 高刺激原文句子的 direct/adapted/omitted 使用情况。")
    if not data.get("tts_readability_report"):
        score -= 10
        issues.append("tts_readability_report 为空，无法判断口播节奏和 TTS 可读性。")
        suggestions.append("检查长句、书面语、连续 OS、TTS 拗口段落。")
    return score, issues, suggestions


def _evaluate_annotations(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    if not data.get("audio_cues"):
        score -= 15
        issues.append("audio_cues 为空，08 配音难以使用语气/停顿信息。")
        suggestions.append("为 N/D/M/S 语音行补充 speaker、emotion、pace、pause_hint、delivery_note。")
    if not data.get("visual_dramatic_units"):
        score -= 18
        issues.append("visual_dramatic_units 为空，06 单帧分镜难以抓动作链和连续性。")
        suggestions.append("为关键语音行补充 scene_name_hint、characters_in_action、props_in_action、action_chain、continuity_hint。")
    if not data.get("storyboard_hints"):
        score -= 10
        issues.append("storyboard_hints 为空，06 分镜难以获得剧本层面的画面锚点。")
        suggestions.append("补充 segment_id / voice_line_id 对应的 visual_anchor、action_chain、shot_intent。")
    if not data.get("visual_executability_report"):
        score -= 10
        issues.append("visual_executability_report 为空，无法提前发现抽象画面动作。")
        suggestions.append("标记抽象、不可画、缺动作链的 segment/visual_unit。")
    if not data.get("character_load_report"):
        score -= 10
        issues.append("character_load_report 为空，无法提前发现单帧人物过多风险。")
        suggestions.append("标记同时上场人物过多的视频单元或视觉单元，并给出拆分建议。")
    if not data.get("continuity_chain"):
        score -= 10
        issues.append("continuity_chain 为空，后续单帧连续性缺少链表约束。")
        suggestions.append("输出 from_visual_unit_id / to_visual_unit_id / must_keep / can_change。")
    return score, issues, suggestions


def _evaluate_final_check(data: dict[str, Any], score: int, issues: list[str], suggestions: list[str]) -> tuple[int, list[str], list[str]]:
    report = data.get("quality_report") or {}
    if isinstance(report, dict) and report.get("needs_retry"):
        score -= 30
        issues.append("02F 总检要求重跑阶段。")
        suggestions.append("按 quality_report.retry_stages 和 revision_instructions 从最早问题阶段重跑。")
    if not data.get("failure_learning_notes"):
        score -= 8
        issues.append("failure_learning_notes 为空，真实测试后难以回灌失败样本。")
        suggestions.append("输出可写入 prompt_tuning_notes.md 的失败类型、观察点、修复策略。")
    return score, issues, suggestions


def build_revision_payload(stage_id: str, original_payload: dict[str, Any], last_output: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "revise_previous_stage_output",
        "stage_id": stage_id,
        "original_input": original_payload,
        "previous_output": last_output,
        "quality_report": quality,
        "instruction": "请严格根据 quality_report.revision_instructions 修正 previous_output，只输出修正后的 JSON 对象，不要输出解释。",
    }
