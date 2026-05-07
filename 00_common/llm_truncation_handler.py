from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")

MAX_CONTINUATIONS = 2
CONTINUABLE_ARRAY_FIELDS: dict[str, list[str]] = {
    "02_script_writer": ["voice_lines", "scenes", "visual_dramatic_units"],
    "03_character_system": ["characters"],
    "04_scene_system": ["scenes"],
    "05_prop_system": ["props"],
    "06_storyboard": ["frames"],
}


def is_truncated(response: dict[str, Any]) -> bool:
    choices = response.get("choices", [])
    if not choices:
        return False
    finish_reason = choices[0].get("finish_reason", "")
    return finish_reason == "length"


def extract_last_content(response: dict[str, Any]) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "") or ""


def find_continuable_array(parsed: dict[str, Any], module_name: str) -> tuple[str, list[Any]] | None:
    fields = CONTINUABLE_ARRAY_FIELDS.get(module_name, [])
    for field in fields:
        arr = parsed.get(field)
        if isinstance(arr, list) and len(arr) > 0:
            return field, arr
    for key, value in parsed.items():
        if isinstance(value, list) and len(value) > 0:
            return key, value
    return None


def get_last_index_info(field_name: str, arr: list[Any]) -> dict[str, Any]:
    if not arr:
        return {"last_index": -1, "last_id": None}
    last = arr[-1] if isinstance(arr[-1], dict) else {}
    last_index = len(arr) - 1
    last_id = last.get("id") or last.get("sequence_index") or last.get("frame_id") or last_index
    return {"last_index": last_index, "last_id": last_id, "last_item_keys": list(last.keys())[:8]}


def build_continuation_prompt(
    module_name: str,
    field_name: str,
    last_index_info: dict[str, Any],
    original_prompt: str,
) -> str:
    last_id = last_index_info.get("last_id")
    last_index = last_index_info.get("last_index", -1)
    return (
        f"你的上一次输出被截断了。请继续输出，但必须遵守以下规则：\n"
        f"1. 不要从头开始，只继续输出缺失的数组元素。\n"
        f"2. 已完成到最后一个 {field_name} 元素，其 id/sequence_index 为 {last_id}（索引 {last_index}）。\n"
        f"3. 从 {last_id} 之后继续输出。\n"
        f"4. 输出必须仍然是合法的 JSON object，格式为 {{\"{field_name}\": [...]}}。\n"
        f"5. 不要重复已输出的内容。\n"
        f"6. 不要改写已完成的内容。\n\n"
        f"原始请求：\n{original_prompt}"
    )


def merge_continuation(
    original_parsed: dict[str, Any],
    continuation_parsed: dict[str, Any],
    field_name: str,
) -> dict[str, Any]:
    original_arr = original_parsed.get(field_name, [])
    continuation_arr = continuation_parsed.get(field_name, [])
    if not isinstance(original_arr, list):
        original_arr = []
    if not isinstance(continuation_arr, list):
        continuation_arr = []
    merged = dict(original_parsed)
    merged[field_name] = original_arr + continuation_arr
    return merged


def write_continuation_trace(
    trace_dir: str | Path,
    continuation_index: int,
    request_prompt: str,
    raw_response: str,
    merged_output: dict[str, Any] | None = None,
) -> None:
    trace_path = Path(trace_dir)
    trace_path.mkdir(parents=True, exist_ok=True)
    idx = continuation_index + 1
    trace_path.joinpath(f"continuation_{idx}_request.json").write_text(
        json.dumps({"prompt": request_prompt}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    trace_path.joinpath(f"continuation_{idx}_raw_response.txt").write_text(
        raw_response, encoding="utf-8"
    )
    if merged_output is not None:
        trace_path.joinpath(f"continuation_{idx}_merged_output.json").write_text(
            json.dumps(merged_output, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def handle_truncation(
    module_name: str,
    original_prompt: str,
    original_response: dict[str, Any],
    original_parsed: dict[str, Any],
    llm_call_fn: Any,
    trace_dir: str | Path | None = None,
    max_continuations: int = MAX_CONTINUATIONS,
) -> dict[str, Any]:
    if not is_truncated(original_response):
        return {"status": "not_truncated", "parsed": original_parsed}

    result = find_continuable_array(original_parsed, module_name)
    if result is None:
        return {
            "status": "truncated_no_continuable_field",
            "parsed": original_parsed,
            "issue_type": "llm_output_truncated",
            "suggested_action": "split_input_or_raise_max_tokens",
        }

    field_name, arr = result
    current_parsed = dict(original_parsed)

    for i in range(max_continuations):
        last_info = get_last_index_info(field_name, arr)
        continuation_prompt = build_continuation_prompt(module_name, field_name, last_info, original_prompt)

        try:
            continuation_response = llm_call_fn(continuation_prompt)
        except Exception as exc:
            return {
                "status": "continuation_llm_error",
                "parsed": current_parsed,
                "continuation_index": i,
                "error": str(exc),
                "issue_type": "llm_output_truncated",
                "suggested_action": "split_input_or_raise_max_tokens",
            }

        raw_content = extract_last_content(continuation_response)
        try:
            continuation_parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            repaired = _try_repair_json(raw_content)
            if repaired is None:
                if trace_dir:
                    write_continuation_trace(trace_dir, i, continuation_prompt, raw_content)
                continue
            continuation_parsed = repaired

        if not isinstance(continuation_parsed, dict):
            if trace_dir:
                write_continuation_trace(trace_dir, i, continuation_prompt, raw_content)
            continue

        merged = merge_continuation(current_parsed, continuation_parsed, field_name)
        if trace_dir:
            write_continuation_trace(trace_dir, i, continuation_prompt, raw_content, merged)

        current_parsed = merged
        arr = current_parsed.get(field_name, [])

        if not is_truncated(continuation_response):
            return {
                "status": "continuation_success",
                "parsed": current_parsed,
                "continuation_count": i + 1,
            }

    return {
        "status": "continuation_exhausted",
        "parsed": current_parsed,
        "continuation_count": max_continuations,
        "issue_type": "llm_output_truncated",
        "suggested_action": "split_input_or_raise_max_tokens",
    }


def _try_repair_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    if not text.startswith("{"):
        start = text.find("{")
        if start < 0:
            return None
        text = text[start:]
    if not text.endswith("}"):
        end = text.rfind("}")
        if end < 0:
            text += "}"
        else:
            text = text[: end + 1]
    if not text.endswith("]"):
        bracket = text.rfind("]")
        if bracket < 0:
            text = text.rstrip() + "]}"
        else:
            text = text[: bracket + 1] + "}"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
