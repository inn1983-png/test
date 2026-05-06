from __future__ import annotations

import json
from typing import Any


REPAIR_SYSTEM_PROMPT = """你是 JSON 修复器。你的任务是把输入中的 broken_json 修复为合法 JSON 对象。
只允许输出 JSON 对象，不要解释，不要 Markdown。
不得新增业务内容，只修复格式、引号、逗号、括号和明显的 JSON 类型错误。
"""


def repair_json_with_llm(client: Any, broken_text: str, error: str) -> dict[str, Any]:
    payload = {
        "error": error,
        "broken_json": broken_text,
        "instruction": "请只输出修复后的 JSON 对象。不要解释。",
    }
    return client.complete_json(REPAIR_SYSTEM_PROMPT, payload)


def ensure_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Expected JSON object")
