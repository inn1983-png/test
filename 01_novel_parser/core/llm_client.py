from __future__ import annotations

import json
import os
import re
import sys
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

    def complete_text(self, system_prompt: str, user_prompt: str, trace_label: str = "LLM") -> str:
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
        if finish_reason == "length":
            raise RuntimeError(
                f"LLM output was truncated by max_tokens. trace={trace_label} chars={len(text)} max_tokens={payload.get('max_tokens')}"
            )
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
        if finish_reason == "length":
            raise RuntimeError(
                f"LLM stream output was truncated by max_tokens. trace={trace_label} chars={len(text)} max_tokens={payload.get('max_tokens')}"
            )
        safe_print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f} finish_reason={finish_reason}")
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
            safe_print(f"[JSON_PARSE] {trace_label} JSON 解析成功 keys={list(parsed.keys())[:12]}")
            return parsed
        except Exception as exc:
            safe_print(f"[JSON_PARSE_ERROR] {trace_label} JSON 解析失败：{exc}")
            if repair_callback is None:
                raise
            safe_print(f"[JSON_REPAIR] {trace_label} 开始调用 JSON 修复")
            repaired = repair_callback(text, str(exc))
            cleaned = prompt_guard.remove_internal_output_fields(repaired)
            safe_print(f"[JSON_REPAIR_DONE] {trace_label} 修复完成 keys={list(cleaned.keys())[:12]}")
            return cleaned


def parse_json_from_text(text: str) -> dict[str, Any]:
    stripped = repair_mojibake_text(text).strip()
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
