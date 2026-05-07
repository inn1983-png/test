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
        from importlib import import_module
        llm_config_utils = import_module("00_common.llm_config_utils")
        base_url = llm_config_utils.resolve_llm_base_url(DEFAULT_TEXT_LLM_BASE_URL)
        model = llm_config_utils.resolve_llm_model(DEFAULT_TEXT_LLM_MODEL)
        api_key = llm_config_utils.resolve_llm_api_key()
        llm_config_utils.validate_api_key_requirement(base_url, api_key, "03_character_system")
        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_sec=llm_config_utils.resolve_llm_timeout(6000),
            temperature=llm_config_utils.resolve_llm_temperature(0.1),
        )


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

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any], repair_callback: Callable[[str, str], dict[str, Any]] | None = None, trace_label: str = "03_character_system", module_name: str = "03_character_system") -> dict[str, Any]:
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
            if llm_streaming.get_last_finish_reason() == "length" and module_name:
                truncation_handler = import_module("00_common.llm_truncation_handler")
                result = truncation_handler.handle_truncation(
                    module_name=module_name,
                    original_prompt=json.dumps(guarded_payload, ensure_ascii=False, indent=2),
                    original_response={"choices": [{"finish_reason": "length", "message": {"content": text}}]},
                    original_parsed=parsed,
                    llm_call_fn=lambda prompt: self._raw_call_for_continuation(prompt, trace_label=f"{trace_label}_cont"),
                    trace_dir=self.trace_output_dir,
                )
                if result.get("status") in ("continuation_success", "continuation_exhausted"):
                    parsed = result["parsed"]
                    if result.get("issue_type") == "llm_output_truncated":
                        llm_streaming.safe_print(f"[LLM_TRUNCATION_EXHAUSTED] {trace_label} 续写次数用尽，使用部分结果")
                    else:
                        llm_streaming.safe_print(f"[LLM_CONTINUATION_OK] {trace_label} 续写成功 continuation_count={result.get('continuation_count', 0)}")
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

    def _raw_call_for_continuation(self, prompt: str, trace_label: str = "LLM_CONT") -> dict[str, Any]:
        import urllib.request
        import urllib.error
        payload: dict[str, Any] = {"model": self.config.model, "temperature": self.config.temperature, "messages": [{"role": "user", "content": prompt}]}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(self.config.base_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                raw = llm_streaming.repair_mojibake_text(response.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            raise RuntimeError(f"Continuation LLM call failed: {exc}") from exc
        return json.loads(raw)


def parse_json_from_text(text: str) -> dict[str, Any]:
    value = llm_trace.parse_json_object_from_text(text, repair_text=llm_streaming.repair_mojibake_text)
    return prompt_guard.remove_internal_output_fields(value)
