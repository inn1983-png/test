from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from importlib import import_module

prompt_guard = import_module("00_common.llm_prompt_guard")

JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
DEFAULT_TEXT_LLM_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_TEXT_LLM_MODEL = "deepseek-v4-pro"


def _sanitize_env_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def _max_tokens_for_trace(trace_label: str) -> int:
    default = int(os.getenv("AI_DRAMA_LLM_MAX_TOKENS", "8192"))
    candidates = []
    if trace_label:
        sanitized = _sanitize_env_key(trace_label)
        candidates.append(f"AI_DRAMA_LLM_MAX_TOKENS_{sanitized}")
        first = sanitized.split("_")[0]
        if first:
            candidates.append(f"AI_DRAMA_LLM_MAX_TOKENS_{first}")
    for key in candidates:
        raw = os.getenv(key)
        if raw is not None and raw.strip():
            return int(raw)
    return default


@dataclass
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    timeout_sec: int
    temperature: float
    stream_log: bool
    max_tokens: int

    @classmethod
    def from_env(cls) -> "LLMConfig":
        base_url = os.getenv("AI_DRAMA_LLM_BASE_URL", DEFAULT_TEXT_LLM_BASE_URL).strip()
        model = os.getenv("AI_DRAMA_LLM_MODEL", DEFAULT_TEXT_LLM_MODEL).strip()
        api_key = os.getenv("AI_DRAMA_LLM_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "01_novel_parser text LLM defaults to DeepSeek V4 Pro API. "
                "Please set AI_DRAMA_LLM_API_KEY. "
                "Optional overrides: AI_DRAMA_LLM_BASE_URL, AI_DRAMA_LLM_MODEL."
            )
        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_sec=int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "6000")),
            temperature=float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", "0.1")),
            stream_log=os.getenv("AI_DRAMA_LLM_STREAM_LOG", "1").strip() not in {"0", "false", "False", "no"},
            max_tokens=int(os.getenv("AI_DRAMA_LLM_MAX_TOKENS", "8192")),
        )


class LLMClient:
    """OpenAI-compatible text LLM client.

    Text phases now default to DeepSeek V4 Pro API for quality and long-context stability.
    Local models should be used separately for vision / multimodal understanding.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def complete_text(self, system_prompt: str, user_prompt: str, trace_label: str = "LLM") -> str:
        if self.config.stream_log:
            try:
                return self._complete_text_stream(system_prompt, user_prompt, trace_label=trace_label)
            except Exception as exc:
                print(f"[LLM_STREAM_FALLBACK] {trace_label} 流式读取失败，切回普通请求：{exc}", flush=True)
        return self._complete_text_once(system_prompt, user_prompt, trace_label=trace_label)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _base_payload(self, system_prompt: str, user_prompt: str, trace_label: str = "LLM") -> dict[str, Any]:
        max_tokens = _max_tokens_for_trace(trace_label)
        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens
        return payload

    def _complete_text_once(self, system_prompt: str, user_prompt: str, trace_label: str) -> str:
        payload = self._base_payload(system_prompt, user_prompt, trace_label=trace_label)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        print(
            f"[LLM_REQUEST] {trace_label} 普通请求 model={self.config.model} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={self.config.base_url}",
            flush=True,
        )
        request = urllib.request.Request(self.config.base_url, data=data, headers=self._headers(), method="POST")
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(
                "LLM API HTTP error:\n"
                f"  status={exc.code} {exc.reason}\n"
                f"  url={self.config.base_url}\n"
                f"  model={self.config.model}\n"
                f"  request_bytes={len(data)}\n"
                f"  max_tokens={payload.get('max_tokens')}\n"
                f"  response_body={body}"
            ) from exc
        result = json.loads(raw)
        text = result["choices"][0]["message"]["content"]
        print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f}", flush=True)
        print(f"[LLM_OUTPUT_PREVIEW] {trace_label} {text[:1200].replace(chr(10), ' ')}", flush=True)
        return text

    def _complete_text_stream(self, system_prompt: str, user_prompt: str, trace_label: str) -> str:
        payload = self._base_payload(system_prompt, user_prompt, trace_label=trace_label)
        payload["stream"] = True
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        print(
            f"[LLM_REQUEST] {trace_label} 流式请求 model={self.config.model} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={self.config.base_url}",
            flush=True,
        )
        request = urllib.request.Request(self.config.base_url, data=data, headers=self._headers(), method="POST")
        chunks: list[str] = []
        printed_chars = 0
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        event = json.loads(line)
                    except Exception:
                        continue
                    choice = (event.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content is None:
                        content = (choice.get("message") or {}).get("content")
                    if not content:
                        continue
                    chunks.append(content)
                    joined_len = sum(len(item) for item in chunks)
                    if joined_len - printed_chars >= 180:
                        preview = "".join(chunks)[printed_chars:joined_len]
                        print(f"[LLM_STREAM] {trace_label} {preview.replace(chr(10), ' ')}", flush=True)
                        printed_chars = joined_len
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(
                "LLM API stream HTTP error:\n"
                f"  status={exc.code} {exc.reason}\n"
                f"  url={self.config.base_url}\n"
                f"  model={self.config.model}\n"
                f"  request_bytes={len(data)}\n"
                f"  max_tokens={payload.get('max_tokens')}\n"
                f"  response_body={body}"
            ) from exc
        text = "".join(chunks)
        if printed_chars < len(text):
            print(f"[LLM_STREAM] {trace_label} {text[printed_chars:].replace(chr(10), ' ')}", flush=True)
        print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f}", flush=True)
        return text

    def complete_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        repair_callback: Callable[[str, str], dict[str, Any]] | None = None,
        trace_label: str = "LLM_JSON",
    ) -> dict[str, Any]:
        guarded_prompt = prompt_guard.apply_json_guard(system_prompt)
        guarded_payload = prompt_guard.compact_payload_hint(user_payload)
        user_prompt = json.dumps(guarded_payload, ensure_ascii=False, indent=2)
        text = self.complete_text(guarded_prompt, user_prompt, trace_label=trace_label)
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
        value = json.loads(stripped[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("LLM output JSON must be an object")
    return prompt_guard.remove_internal_output_fields(value)
