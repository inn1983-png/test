from __future__ import annotations

import json
from typing import Any


def repair_json_with_llm(client: Any, broken_json: str, error: str) -> dict[str, Any]:
    system_prompt = """
你是 JSON 修复器。只修复 JSON 语法，不新增业务内容，不改写字段含义。
必须只输出一个 JSON object，不要输出 Markdown。
""".strip()
    payload = {"error": error, "broken_json": broken_json}
    text = client.complete_text(system_prompt, json.dumps(payload, ensure_ascii=False, indent=2))
    from 03_character_system.core.llm_client import parse_json_from_text  # type: ignore

    return parse_json_from_text(text)
