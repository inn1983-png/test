from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "06A": ["asset_availability_report", "allowed_asset_names", "upstream_blocking_issues", "storyboard_scope"],
    "06B": ["storyboard_plan", "frame_group_plan", "coverage_plan", "risk_report"],
    "06C": ["frames"],
    "06D": ["continuity_map", "four_grid_preview_groups", "frame_transition_report"],
    "06E": ["quality_report", "evidence_index", "revision_plan", "upstream_blocking_issues"],
}

VALID_RETRY_STAGES = {"06A", "06B", "06C", "06D"}
FORBIDDEN_FIELDS = {"prompt", "image_prompt", "desc_prompt", "desc_promopt", "negative_prompt", "video_prompt", "comfyui_prompt"}


def _non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _has_forbidden_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in FORBIDDEN_FIELDS:
                return True
            if _has_forbidden_field(child):
                return True
    elif isinstance(value, list):
        return any(_has_forbidden_field(item) for item in value)
    return False


def evaluate_stage(stage_id: str, data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    score = 100
    for field in REQUIRED_BY_STAGE.get(stage_id, []):
        if not _non_empty(data.get(field)):
            issues.append(f"缺少或为空：{field}")
            score -= 18
    if _has_forbidden_field(data):
        issues.append("06 不能输出图像/视频/ComfyUI 提示词字段，只能写 reference_requirements / composition_notes / continuity_notes")
        score -= 35

    if stage_id == "06A":
        allowed = data.get("allowed_asset_names", {}) if isinstance(data.get("allowed_asset_names"), dict) else {}
        for key in ["characters", "scenes", "props"]:
            if key not in allowed or not isinstance(allowed.get(key), list):
                issues.append(f"allowed_asset_names.{key} 必须为数组")
                score -= 10
        report = data.get("asset_availability_report", {}) if isinstance(data.get("asset_availability_report"), dict) else {}
        if "ready" not in report:
            issues.append("asset_availability_report 必须包含 ready 字段")
            score -= 10
    if stage_id == "06B":
        plans = data.get("frame_group_plan", []) or []
        if not isinstance(plans, list) or not plans:
            issues.append("frame_group_plan 不能为空")
            score -= 20
    if stage_id == "06C":
        frames = data.get("frames", []) or []
        if not isinstance(frames, list) or not frames:
            issues.append("frames 不能为空")
            score -= 30
        seen: set[str] = set()
        for idx, frame in enumerate(frames):
            if not isinstance(frame, dict):
                issues.append(f"frames[{idx}] 不是对象")
                score -= 10
                continue
            for field in ["frame_id", "sequence_index", "source_segment_ids", "source_voice_line_ids", "scene", "characters", "props", "story_action", "emotion", "camera_plan", "reference_requirements", "composition_notes", "continuity_notes"]:
                if field not in frame:
                    issues.append(f"分镜 {frame.get('frame_id', idx)} 缺少字段：{field}")
                    score -= 5
            fid = str(frame.get("frame_id", "")).strip()
            if fid in seen:
                issues.append(f"frame_id 重复：{fid}")
                score -= 10
            if fid:
                seen.add(fid)
            if not isinstance(frame.get("characters", []), list) or not isinstance(frame.get("props", []), list):
                issues.append(f"分镜 {fid or idx} characters/props 必须为数组")
                score -= 8
    if stage_id in {"06D", "06E"}:
        qr_key = "quality_report" if stage_id == "06E" else "frame_transition_report"
        report = data.get(qr_key, {}) if isinstance(data.get(qr_key), dict) else {}
        if report.get("needs_retry") and not report.get("retry_stages"):
            issues.append(f"{stage_id} 要求重跑但未给 retry_stages")
            score -= 20
        for retry_stage in report.get("retry_stages", []) or []:
            if retry_stage not in VALID_RETRY_STAGES:
                issues.append(f"{stage_id} retry_stages 非法：{retry_stage}")
                score -= 10
        if report.get("needs_retry") and not report.get("revision_instructions"):
            issues.append(f"{stage_id} 需要重跑但没有 revision_instructions")
            score -= 15
    score = max(0, min(100, score))
    revision_instructions = [f"请修复：{issue}" for issue in issues]
    return {"score": score, "passed": score >= THRESHOLD, "issues": issues, "revision_instructions": revision_instructions}


def build_revision_payload(stage_id: str, original_payload: dict[str, Any], previous_output: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "original_payload": original_payload,
        "previous_output": previous_output,
        "revision_instructions": quality.get("revision_instructions", []),
        "task": f"重跑 {stage_id}。必须保留完整 JSON 字段，只修复评分指出的问题。06 不允许输出图像提示词或新增资产。",
    }
