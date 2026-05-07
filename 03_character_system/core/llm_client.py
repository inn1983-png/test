from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from importlib import import_module

prompt_guard = import_module("00_common.llm_prompt_guard")
llm_streaming = import_module("00_common.llm_streaming")
llm_trace = import_module("00_common.llm_trace")

JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
DEFAULT_TEXT_LLM_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_TEXT_LLM_MODEL = "deepseek-v4-pro"


@dataclass
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    timeout_sec: int
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        base_url = os.getenv("AI_DRAMA_LLM_BASE_URL", DEFAULT_TEXT_LLM_BASE_URL).strip()
        model = os.getenv("AI_DRAMA_LLM_MODEL", DEFAULT_TEXT_LLM_MODEL).strip()
        api_key = os.getenv("AI_DRAMA_LLM_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("03_character_system text LLM defaults to DeepSeek V4 Pro API. Please set AI_DRAMA_LLM_API_KEY. Optional overrides: AI_DRAMA_LLM_BASE_URL, AI_DRAMA_LLM_MODEL.")
        return cls(base_url=base_url, model=model, api_key=api_key, timeout_sec=int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "6000")), temperature=float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", "0.1")))


class LLMClient:
    """OpenAI-compatible text LLM client for character asset stages."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        llm_streaming.force_utf8_stdio()
        self.config = config or LLMConfig.from_env()
        self.trace_output_dir: str | Path | None = None

    def set_trace_output_dir(self, output_dir: str | Path | None) -> None:
        self.trace_output_dir = output_dir

    def complete_text(self, system_prompt: str, user_prompt: str, trace_label: str = "03_character_system") -> str:
        return llm_streaming.complete_text_with_logs(base_url=self.config.base_url, model=self.config.model, api_key=self.config.api_key, timeout_sec=self.config.timeout_sec, temperature=self.config.temperature, system_prompt=system_prompt, user_prompt=user_prompt, trace_label=trace_label)

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any], repair_callback: Callable[[str, str], dict[str, Any]] | None = None, trace_label: str = "03_character_system") -> dict[str, Any]:
        guarded_prompt = prompt_guard.apply_json_guard(system_prompt)
        guarded_payload = prompt_guard.compact_payload_hint(user_payload)
        trace = llm_trace.start_trace(self.trace_output_dir, trace_label)
        trace.write_request({"trace_label": trace_label, "model": self.config.model, "base_url": self.config.base_url, "temperature": self.config.temperature, "timeout_sec": self.config.timeout_sec, "has_api_key": bool(self.config.api_key), "system_prompt": guarded_prompt, "user_payload": guarded_payload})
        text = self.complete_text(guarded_prompt, json.dumps(guarded_payload, ensure_ascii=False, indent=2), trace_label=trace_label)
        trace.write_raw_response(text)
        try:
            parsed_before = llm_trace.parse_json_object_from_text(text, repair_text=llm_streaming.repair_mojibake_text)
            trace.write_parsed_before_clean(parsed_before)
            parsed = prompt_guard.remove_internal_output_fields(parsed_before)
            trace.write_parsed_after_clean(parsed)
            trace.write_final_stage_output(parsed)
            llm_streaming.safe_print(f"[JSON_PARSE] {trace_label} JSON 解析成功 keys={list(parsed.keys())[:12]}")
            return parsed
        except Exception as exc:
            llm_streaming.safe_print(f"[JSON_PARSE_ERROR] {trace_label} JSON 解析失败：{exc}")
            if repair_callback is None:
                raise
            llm_streaming.safe_print(f"[JSON_REPAIR] {trace_label} 开始调用 JSON 修复")
            trace.write_repair_request(text, str(exc))
            repaired = repair_callback(text, str(exc))
            cleaned = prompt_guard.remove_internal_output_fields(repaired)
            trace.write_repair_response(repaired)
            trace.write_parsed_after_clean(cleaned)
            trace.write_final_stage_output(cleaned)
            llm_streaming.safe_print(f"[JSON_REPAIR_DONE] {trace_label} 修复完成 keys={list(cleaned.keys())[:12]}")
            return cleaned


def parse_json_from_text(text: str) -> dict[str, Any]:
    value = llm_trace.parse_json_object_from_text(text, repair_text=llm_streaming.repair_mojibake_text)
    return prompt_guard.remove_internal_output_fields(value)
