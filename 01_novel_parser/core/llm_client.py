from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from importlib import import_module

prompt_guard = import_module("00_common.llm_prompt_guard")
llm_trace = import_module("00_common.llm_trace")

JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
DEFAULT_TEXT_LLM_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_TEXT_LLM_MODEL = "deepseek-v4-pro"
MOJIBAKE_MARKERS = ("�", "½", "¼", "¾", "Ã", "Â")


def _force_utf8_stdio() -> None:
    """Force UTF-8 stdout/stderr inside module subprocesses.

    Windows console / pipe encoding can otherwise turn Chinese LLM stream logs into
    replacement-character mojibake before the Web UI even receives them.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_force_utf8_stdio()


def safe_print(message: str) -> None:
    text = str(message)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()


def repair_mojibake_text(text: str) -> str:
    if not text or not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text

    def cjk_score(value: str) -> int:
        return sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")

    def bad_score(value: str) -> int:
        return value.count("�") * 4 + sum(value.count(ch) for ch in MOJIBAKE_MARKERS if ch != "�")

    candidates = [text]
    for source, target in (("latin1", "utf-8"), ("latin1", "gbk"), ("cp1252", "utf-8"), ("cp1252", "gbk"), ("gbk", "utf-8")):
        try:
            candidates.append(text.encode(source, errors="ignore").decode(target, errors="ignore"))
        except Exception:
            pass
    best = max(candidates, key=lambda item: (cjk_score(item) - bad_score(item), cjk_score(item), -bad_score(item), len(item)))
    if cjk_score(best) > cjk_score(text) and bad_score(best) <= bad_score(text):
        return best
    return text


def _sanitize_env_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def _max_tokens_for_trace(trace_label: str) -> int:
    default = int(os.getenv("AI_DRAMA_LLM_MAX_TOKENS", "16384"))
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
        from importlib import import_module
        llm_config_utils = import_module("00_common.llm_config_utils")
        base_url = llm_config_utils.resolve_llm_base_url(DEFAULT_TEXT_LLM_BASE_URL)
        model = llm_config_utils.resolve_llm_model(DEFAULT_TEXT_LLM_MODEL)
        api_key = llm_config_utils.resolve_llm_api_key()
        llm_config_utils.validate_api_key_requirement(base_url, api_key, "01_novel_parser")
        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_sec=llm_config_utils.resolve_llm_timeout(6000),
            temperature=llm_config_utils.resolve_llm_temperature(0.1),
            stream_log=os.getenv("AI_DRAMA_LLM_STREAM_LOG", "1").strip() not in {"0", "false", "False", "no"},
            max_tokens=int(os.getenv("AI_DRAMA_LLM_MAX_TOKENS", "16384")),
        )


class LLMClient:
    """OpenAI-compatible text LLM client.

    Text phases default to DeepSeek V4 Pro API for quality and long-context stability.
    Local models should be used separately for vision / multimodal understanding.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        _force_utf8_stdio()
        self.config = config or LLMConfig.from_env()
        self.trace_output_dir: str | Path | None = None
        self.last_finish_reason: str | None = None

    def set_trace_output_dir(self, output_dir: str | Path | None) -> None:
        self.trace_output_dir = output_dir

    def complete_text(self, system_prompt: str, user_prompt: str, trace_label: str = "LLM") -> str:
        self.last_finish_reason = None
        if self.config.stream_log:
            try:
                return self._complete_text_stream(system_prompt, user_prompt, trace_label=trace_label)
            except Exception as exc:
                safe_print(f"[LLM_STREAM_FALLBACK] {trace_label} 流式读取失败，切回普通请求：{exc}")
        return self._complete_text_once(system_prompt, user_prompt, trace_label=trace_label)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json; charset=utf-8"}
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

    def _decode_response_bytes(self, raw: bytes, response: Any | None = None) -> str:
        charset = "utf-8"
        try:
            header_charset = response.headers.get_content_charset() if response is not None else None
            if header_charset:
                charset = header_charset
        except Exception:
            pass
        return repair_mojibake_text(raw.decode(charset, errors="replace"))

    def _complete_text_once(self, system_prompt: str, user_prompt: str, trace_label: str) -> str:
        payload = self._base_payload(system_prompt, user_prompt, trace_label=trace_label)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        safe_print(
            f"[LLM_REQUEST] {trace_label} 普通请求 model={self.config.model} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={self.config.base_url}"
        )
        request = urllib.request.Request(self.config.base_url, data=data, headers=self._headers(), method="POST")
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                raw = self._decode_response_bytes(response.read(), response)
        except urllib.error.HTTPError as exc:
            body = self._decode_response_bytes(exc.read(), exc) if exc.fp else ""
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
        choice = result["choices"][0]
        finish_reason = choice.get("finish_reason")
        text = repair_mojibake_text(choice["message"]["content"])
        self.last_finish_reason = finish_reason
        if finish_reason == "length":
            safe_print(f"[LLM_TRUNCATED] {trace_label} 输出被截断 chars={len(text)} max_tokens={payload.get('max_tokens')}")
        else:
            safe_print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f} finish_reason={finish_reason}")
        safe_print(f"[LLM_OUTPUT_PREVIEW] {trace_label} {text[:1200].replace(chr(10), ' ')}")
        return text

    def _complete_text_stream(self, system_prompt: str, user_prompt: str, trace_label: str) -> str:
        payload = self._base_payload(system_prompt, user_prompt, trace_label=trace_label)
        payload["stream"] = True
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        safe_print(
            f"[LLM_REQUEST] {trace_label} 流式请求 model={self.config.model} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={self.config.base_url}"
        )
        request = urllib.request.Request(self.config.base_url, data=data, headers=self._headers(), method="POST")
        chunks: list[str] = []
        printed_chars = 0
        finish_reason: str | None = None
        start = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                for raw_line in response:
                    line = self._decode_response_bytes(raw_line, response).strip()
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
                    if choice.get("finish_reason"):
                        finish_reason = choice.get("finish_reason")
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if content is None:
                        content = (choice.get("message") or {}).get("content")
                    if not content:
                        continue
                    content = repair_mojibake_text(content)
                    chunks.append(content)
                    joined_len = sum(len(item) for item in chunks)
                    if joined_len - printed_chars >= 180:
                        preview = "".join(chunks)[printed_chars:joined_len]
                        safe_print(f"[LLM_STREAM] {trace_label} {preview.replace(chr(10), ' ')}")
                        printed_chars = joined_len
        except urllib.error.HTTPError as exc:
            body = self._decode_response_bytes(exc.read(), exc) if exc.fp else ""
            raise RuntimeError(
                "LLM API stream HTTP error:\n"
                f"  status={exc.code} {exc.reason}\n"
                f"  url={self.config.base_url}\n"
                f"  model={self.config.model}\n"
                f"  request_bytes={len(data)}\n"
                f"  max_tokens={payload.get('max_tokens')}\n"
                f"  response_body={body}"
            ) from exc
        text = repair_mojibake_text("".join(chunks))
        if printed_chars < len(text):
            safe_print(f"[LLM_STREAM] {trace_label} {text[printed_chars:].replace(chr(10), ' ')}")
        self.last_finish_reason = finish_reason
        if finish_reason == "length":
            safe_print(f"[LLM_TRUNCATED] {trace_label} 流式输出被截断 chars={len(text)} max_tokens={payload.get('max_tokens')}")
        else:
            safe_print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f} finish_reason={finish_reason}")
        return text

    def complete_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        repair_callback: Callable[[str, str], dict[str, Any]] | None = None,
        trace_label: str = "LLM_JSON",
        module_name: str = "",
    ) -> dict[str, Any]:
        guarded_prompt = prompt_guard.apply_json_guard(system_prompt)
        guarded_payload = prompt_guard.compact_payload_hint(user_payload)
        user_prompt = json.dumps(guarded_payload, ensure_ascii=False, indent=2)
        trace = llm_trace.start_trace(self.trace_output_dir, trace_label)
        trace.write_request(
            {
                "trace_label": trace_label,
                "model": self.config.model,
                "base_url": self.config.base_url,
                "temperature": self.config.temperature,
                "timeout_sec": self.config.timeout_sec,
                "max_tokens": _max_tokens_for_trace(trace_label),
                "has_api_key": bool(self.config.api_key),
                "system_prompt": guarded_prompt,
                "user_payload": guarded_payload,
            }
        )
        text = self.complete_text(guarded_prompt, user_prompt, trace_label=trace_label)
        trace.write_raw_response(text)
        try:
            parsed_before = llm_trace.parse_json_object_from_text(text, repair_text=repair_mojibake_text)
            trace.write_parsed_before_clean(parsed_before)
            parsed = prompt_guard.remove_internal_output_fields(parsed_before)
            trace.write_parsed_after_clean(parsed)
            if self.last_finish_reason == "length" and module_name:
                truncation_handler = import_module("00_common.llm_truncation_handler")
                result = truncation_handler.handle_truncation(
                    module_name=module_name,
                    original_prompt=user_prompt,
                    original_response={"choices": [{"finish_reason": "length", "message": {"content": text}}]},
                    original_parsed=parsed,
                    llm_call_fn=lambda prompt: self._raw_call_for_continuation(prompt, trace_label=f"{trace_label}_cont"),
                    trace_dir=self.trace_output_dir,
                )
                if result.get("status") in ("continuation_success", "continuation_exhausted"):
                    parsed = result["parsed"]
                    if result.get("issue_type") == "llm_output_truncated":
                        safe_print(f"[LLM_TRUNCATION_EXHAUSTED] {trace_label} 续写次数用尽，使用部分结果")
                    else:
                        safe_print(f"[LLM_CONTINUATION_OK] {trace_label} 续写成功 continuation_count={result.get('continuation_count', 0)}")
            trace.write_final_stage_output(parsed)
            safe_print(f"[JSON_PARSE] {trace_label} JSON 解析成功 keys={list(parsed.keys())[:12]}")
            return parsed
        except Exception as exc:
            safe_print(f"[JSON_PARSE_ERROR] {trace_label} JSON 解析失败：{exc}")
            if repair_callback is None:
                raise
            safe_print(f"[JSON_REPAIR] {trace_label} 开始调用 JSON 修复")
            trace.write_repair_request(text, str(exc))
            repaired = repair_callback(text, str(exc))
            cleaned = prompt_guard.remove_internal_output_fields(repaired)
            trace.write_repair_response(repaired)
            trace.write_parsed_after_clean(cleaned)
            trace.write_final_stage_output(cleaned)
            safe_print(f"[JSON_REPAIR_DONE] {trace_label} 修复完成 keys={list(cleaned.keys())[:12]}")
            return cleaned

    def _raw_call_for_continuation(self, prompt: str, trace_label: str = "LLM_CONT") -> dict[str, Any]:
        payload = self._base_payload("", prompt, trace_label=trace_label)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.config.base_url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
                raw = self._decode_response_bytes(response.read(), response)
        except Exception as exc:
            raise RuntimeError(f"Continuation LLM call failed: {exc}") from exc
        return json.loads(raw)


def parse_json_from_text(text: str) -> dict[str, Any]:
    value = llm_trace.parse_json_object_from_text(text, repair_text=repair_mojibake_text)
    return prompt_guard.remove_internal_output_fields(value)
