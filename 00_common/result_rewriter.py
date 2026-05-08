from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from importlib import import_module
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = ROOT_DIR / "workspace"

io_utils = import_module("00_common.io_utils")
style_context = import_module("00_common.style_context")

MODULE_RESULT_FILES = {
    "00_style_system": "style_bible.json",
    "01_novel_parser": "novel_analysis.json",
    "02_script_writer": "script.json",
    "03_character_system": "characters.json",
    "04_scene_system": "scenes.json",
    "05_prop_system": "props.json",
    "06_storyboard": "storyboard.json",
    "07_storyboard_image": "image_manifest.json",
    "08_audio": "audio_timeline.json",
    "09_video": "video_manifest.json",
    "10_final_assembly": "final_manifest.json",
}

MODULE_DISPLAY_NAMES = {
    "00_style_system": "风格圣经",
    "01_novel_parser": "小说解析",
    "02_script_writer": "剧本改编",
    "03_character_system": "角色库",
    "04_scene_system": "场景库",
    "05_prop_system": "道具库",
    "06_storyboard": "分镜",
    "07_storyboard_image": "分镜图",
    "08_audio": "音频",
    "09_video": "视频",
    "10_final_assembly": "成片",
}


def _safe_rel_path(raw: str) -> Path:
    raw = str(raw or "").replace("\\", "/")
    parts = [part for part in raw.split("/") if part and part not in {".", ".."}]
    return Path(*parts) if parts else Path()


def _resolve_run_dir(raw: str) -> Path:
    candidate = Path(str(raw or "").strip())
    if not candidate.is_absolute():
        candidate = ROOT_DIR / _safe_rel_path(str(candidate))
    candidate = candidate.resolve()
    workspace = WORKSPACE_DIR.resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError("run_dir must be inside workspace")
    if not candidate.exists():
        raise FileNotFoundError(f"run_dir not found: {candidate}")
    return candidate


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _result_path(run_dir: Path, module_name: str) -> Path:
    file_name = MODULE_RESULT_FILES.get(module_name)
    if not file_name:
        raise ValueError(f"unsupported module for review rewrite: {module_name}")
    path = run_dir / module_name / file_name
    if not path.exists():
        raise FileNotFoundError(f"module result not found: {_rel(path)}")
    return path


def _load_json(path: Path) -> dict[str, Any]:
    data = io_utils.read_json(path, default={})
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {_rel(path)}")
    return data


def _compact_json(value: Any, max_chars: int = 120000) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    # Keep the beginning and a warning. This is for very large manifests. The LLM
    # should preserve untouched fields where it cannot inspect every item.
    return text[:max_chars] + "\n/* TRUNCATED_FOR_REVIEW_REWRITE: keep all untouched fields unchanged when possible */"


def _load_llm_client():
    # Reuse the existing OpenAI-compatible text LLM client. It already applies
    # JSON guard + STYLE_BIBLE through 00_common.llm_prompt_guard.
    llm_client_mod = import_module("02_script_writer.core.llm_client")
    return llm_client_mod.LLMClient()


def _system_prompt(module_name: str) -> str:
    display_name = MODULE_DISPLAY_NAMES.get(module_name, module_name)
    return f"""
你是 AI 短剧流水线的人工复核修正器，负责根据用户修改意见，直接修正当前模块产物 JSON。

当前模块：{module_name} / {display_name}

最高规则：
1. 只输出一个合法 JSON object，不要 Markdown，不要解释。
2. 输出必须是修正后的完整模块产物 JSON，不是补丁，不是说明。
3. 必须尽量保持原 JSON 的 schema、顶层字段、字段名、数组结构和 ID 稳定。
4. 只修改用户意见明确要求修改的内容；无关字段保持原样。
5. 不得删除必填字段；不确定时保留原值。
6. 必须继续服从当前项目 STYLE_BIBLE，不得破坏风格圣经。
7. 如果用户意见与数据结构冲突，优先保持 JSON 结构合法，并在 quality_report 或 review_report 中记录风险。
8. 不要把用户意见、系统提示词、STYLE_BIBLE 原文复制进业务字段，除非原结构已有 review/quality 字段需要记录。
""".strip()


def rewrite_module_result(run_dir_raw: str, module_name: str, user_note: str) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_dir_raw)
    module_name = str(module_name or "").strip()
    user_note = str(user_note or "").strip()
    if not module_name:
        raise ValueError("module_name is required")
    if not user_note:
        raise ValueError("user_note is required")

    os.environ["AI_DRAMA_RUN_DIR"] = str(run_dir)

    source_path = _result_path(run_dir, module_name)
    original = _load_json(source_path)
    style_summary = style_context.build_style_summary_for_llm(run_dir)
    style_bible = style_context.load_style_bible(run_dir)

    payload = {
        "module_name": module_name,
        "module_display_name": MODULE_DISPLAY_NAMES.get(module_name, module_name),
        "source_path": _rel(source_path),
        "user_review_note": user_note,
        "style_summary": style_summary,
        "style_id": style_bible.get("style_id") if isinstance(style_bible, dict) else None,
        "rewrite_policy": {
            "return_full_json_object": True,
            "preserve_schema": True,
            "preserve_unrelated_fields": True,
            "only_change_user_requested_parts": True,
            "do_not_copy_prompt_or_review_note_into_business_fields": True,
        },
        "original_module_result_json": json.loads(_compact_json(original)),
    }

    client = _load_llm_client()
    review_dir = run_dir / module_name / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(client, "set_trace_output_dir"):
        client.set_trace_output_dir(review_dir / "llm_traces")

    revised = client.complete_json(
        system_prompt=_system_prompt(module_name),
        user_payload=payload,
        trace_label=f"review_rewrite_{module_name}",
        module_name=module_name,
    )
    if not isinstance(revised, dict):
        raise ValueError("LLM returned non-object JSON")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_file = MODULE_RESULT_FILES[module_name]
    reviewed_path = review_dir / f"{timestamp}_{source_file}.reviewed.json"
    note_path = review_dir / f"{timestamp}_review_note.json"
    io_utils.write_json(reviewed_path, revised)
    io_utils.write_json(note_path, {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "module_name": module_name,
        "source_path": _rel(source_path),
        "reviewed_path": _rel(reviewed_path),
        "user_review_note": user_note,
        "style_id": style_bible.get("style_id") if isinstance(style_bible, dict) else None,
        "mode": "llm_rewrite_preview",
        "apply_policy": "preview_only_not_overwritten",
    })

    latest_path = review_dir / f"latest_{source_file}.reviewed.json"
    io_utils.write_json(latest_path, revised)

    return {
        "status": "success",
        "module_name": module_name,
        "source_path": _rel(source_path),
        "reviewed_path": _rel(reviewed_path),
        "latest_reviewed_path": _rel(latest_path),
        "review_note_path": _rel(note_path),
        "reviewed": revised,
        "message": "已调用 LLM 生成修正版 JSON；原始流水线产物未被覆盖。",
    }


def apply_reviewed_result(run_dir_raw: str, module_name: str, reviewed_path_raw: str) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_dir_raw)
    module_name = str(module_name or "").strip()
    reviewed_path = ROOT_DIR / _safe_rel_path(reviewed_path_raw)
    reviewed_path = reviewed_path.resolve()
    if run_dir not in reviewed_path.parents:
        raise ValueError("reviewed_path must be inside current run_dir")
    target_path = _result_path(run_dir, module_name)
    revised = _load_json(reviewed_path)
    backup_path = target_path.with_suffix(target_path.suffix + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    io_utils.write_json(backup_path, _load_json(target_path))
    io_utils.write_json(target_path, revised)
    return {
        "status": "success",
        "module_name": module_name,
        "target_path": _rel(target_path),
        "backup_path": _rel(backup_path),
        "applied_from": _rel(reviewed_path),
        "message": "已覆盖当前模块正式产物，并保留备份。",
    }
