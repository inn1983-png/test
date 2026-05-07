from __future__ import annotations

import json
from importlib import import_module
from typing import Any

prompt_guard = import_module("00_common.llm_prompt_guard")


def repair_json_with_llm(client: Any, broken_json: str, error: str) -> dict[str, Any]:
    system_prompt = prompt_guard.apply_json_guard(
        """
你是 JSON 修复器。只修复 JSON 语法，不新增业务内容，不改写字段含义。
必须只输出修复后的 JSON object 本身。
""".strip(),
        stage_id="json_repair",
    )
    payload = prompt_guard.compact_payload_hint({"error": error, "broken_json": broken_json})
    text = client.complete_text(system_prompt, json.dumps(payload, ensure_ascii=False, indent=2))
    llm_client = import_module("05_prop_system.core.llm_client")
    return llm_client.parse_json_from_text(text)
