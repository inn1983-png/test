from __future__ import annotations

from typing import Any

THRESHOLD = 80

REQUIRED_BY_STAGE = {
    "06A": ["asset_availability_report", "allowed_asset_names", "upstream_blocking_issues", "storyboard_scope"],
    "06B": ["storyboard_plan", "frame_group_plan", "coverage_plan", "risk_report"],
    "06C": ["appearance_asset_requirements", "frames"],
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
        issues.append("06 不能输出图像/视频/ComfyUI 提示词字段，只能写 reference_requirements / composition_notes / continuity_notes / appearance_asset_key")
        score -= 35

    if stage_id == "06A":
        allowed = data.get("allowed_asset_names", {}) if isinstance(data.get("allowed_asset_names"), dict) else {}
        for key in ["characters", "character_costumes", "scenes", "props", "mergeable_wearable_props", "independent_prop_refs"]:
            if key not in allowed or not isinstance(allowed.get(key), list):
                issues.append(f"allowed_asset_names.{key} 必须为数组")
                score -= 8
        report = data.get("asset_availability_report", {}) if isinstance(data.get("asset_availability_report"), dict) else {}
        if "ready" not in report:
            issues.append("asset_availability_report 必须包含 ready 字段")
            score -= 10
        if "appearance_asset_readiness" not in report:
            issues.append("asset_availability_report 必须包含 appearance_asset_readiness")
            score -= 8
    if stage_id == "06B":
        plans = data.get("frame_group_plan", []) or []
        if not isinstance(plans, list) or not plans:
            issues.append("frame_group_plan 不能为空")
            score -= 20
    if stage_id == "06C":
        appearance_reqs = data.get("appearance_asset_requirements", []) or []
        if not isinstance(appearance_reqs, list) or not appearance_reqs:
            issues.append("appearance_asset_requirements 不能为空，06C 必须先定义角色定妆/造型照需求")
            score -= 18
        for idx, req in enumerate(appearance_reqs):
            if not isinstance(req, dict):
                issues.append(f"appearance_asset_requirements[{idx}] 不是对象")
                score -= 8
                continue
            for field in ["appearance_asset_key", "canonical_name", "character_lock_reference", "costume_id", "wearable_props", "source_frame_ids", "usage_note"]:
                if field not in req:
                    issues.append(f"造型资产需求缺少字段：{field}")
                    score -= 4
            if not isinstance(req.get("wearable_props", []), list):
                issues.append("appearance_asset_requirements.wearable_props 必须为数组")
                score -= 5
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
            for char in frame.get("characters", []) or []:
                if isinstance(char, dict):
                    for field in ["canonical_name", "costume_id", "appearance_asset_key", "character_lock_reference", "wearable_props"]:
                        if field not in char:
                            issues.append(f"分镜 {fid or idx} 角色缺少字段：{field}")
                            score -= 4
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
