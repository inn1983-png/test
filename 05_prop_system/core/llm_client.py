from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable
from importlib import import_module

prompt_guard = import_module("00_common.llm_prompt_guard")
llm_streaming = import_module("00_common.llm_streaming")

JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


@dataclass
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    timeout_sec: int
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        base_url = os.getenv("AI_DRAMA_LLM_BASE_URL", "").strip()
        model = os.getenv("AI_DRAMA_LLM_MODEL", "").strip()
        if not base_url or not model:
            raise RuntimeError("05_prop_system requires a real local LLM. Please set AI_DRAMA_LLM_BASE_URL and AI_DRAMA_LLM_MODEL.")
        return cls(base_url=base_url, model=model, api_key=os.getenv("AI_DRAMA_LLM_API_KEY", ""), timeout_sec=int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "6000")), temperature=float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", "0.1")))


class LLMClient:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def complete_text(self, system_prompt: str, user_prompt: str, trace_label: str = "05_prop_system") -> str:
        return llm_streaming.complete_text_with_logs(
            base_url=self.config.base_url,
            model=self.config.model,
            api_key=self.config.api_key,
            timeout_sec=self.config.timeout_sec,
            temperature=self.config.temperature,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            trace_label=trace_label,
        )

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any], repair_callback: Callable[[str, str], dict[str, Any]] | None = None, trace_label: str = "05_prop_system") -> dict[str, Any]:
        guarded_prompt = prompt_guard.apply_json_guard(system_prompt)
        guarded_payload = prompt_guard.compact_payload_hint(user_payload)
        text = self.complete_text(guarded_prompt, json.dumps(guarded_payload, ensure_ascii=False, indent=2), trace_label=trace_label)
        try:
            parsed = parse_json_from_text(text)
            print(f"[JSON_PARSE] {trace_label} JSON 解析成功 keys={list(parsed.keys())[:12]}", flush=True)
            return parsed
        except Exception as exc:
            print(f"[JSON_PARSE_ERROR] {trace_label} JSON 解析失败：{exc}", flush=True)
            if repair_callback is None:
                raise
            print(f"[JSON_REPAIR] {trace_label} 开始调用 JSON 修复", flush=True)
            repaired = repair_callback(text, str(exc))
            cleaned = prompt_guard.remove_internal_output_fields(repaired)
            print(f"[JSON_REPAIR_DONE] {trace_label} 修复完成 keys={list(cleaned.keys())[:12]}", flush=True)
            return cleaned


def parse_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    match = JSON_RE.search(stripped)
    if match:
        stripped = match.group(1).strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise
        value = json.loads(stripped[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM output JSON must be an object")
    return prompt_guard.remove_internal_output_fields(value)
