from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

MOJIBAKE_MARKERS = ("�", "½", "¼", "¾", "Ã", "Â")


def force_utf8_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


force_utf8_stdio()


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


def stream_log_enabled() -> bool:
    return os.getenv("AI_DRAMA_LLM_STREAM_LOG", "1").strip().lower() not in {"0", "false", "no"}


def default_max_tokens() -> int:
    """Default completion cap for staged JSON calls.

    Text LLM now defaults to DeepSeek V4 Pro API. 16384 is safer for JSON stages
    such as asset extraction and storyboard generation. Set AI_DRAMA_LLM_MAX_TOKENS=0
    to disable globally, or use stage-specific env vars.
    """
    return int(os.getenv("AI_DRAMA_LLM_MAX_TOKENS", "16384"))


def _sanitize_env_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()


def max_tokens_for_trace(trace_label: str) -> int:
    """Allow coarse or stage-specific output caps.

    Examples:
      AI_DRAMA_LLM_MAX_TOKENS=32768
      AI_DRAMA_LLM_MAX_TOKENS_01A=4096
      AI_DRAMA_LLM_MAX_TOKENS_06_STORYBOARD=20000
    """
    default = default_max_tokens()
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


def build_headers(api_key: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _apply_generation_controls(payload: dict[str, Any], trace_label: str) -> dict[str, Any]:
    payload = dict(payload)
    max_tokens = max_tokens_for_trace(trace_label)
    if max_tokens > 0:
        payload["max_tokens"] = max_tokens
    return payload


def _decode_response_bytes(raw: bytes, response: Any | None = None) -> str:
    charset = "utf-8"
    try:
        header_charset = response.headers.get_content_charset() if response is not None else None
        if header_charset:
            charset = header_charset
    except Exception:
        pass
    return repair_mojibake_text(raw.decode(charset, errors="replace"))


def complete_text_with_logs(
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout_sec: int,
    temperature: float,
    system_prompt: str,
    user_prompt: str,
    trace_label: str,
) -> str:
    force_utf8_stdio()
    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    payload = _apply_generation_controls(payload, trace_label)
    if stream_log_enabled():
        try:
            return _complete_stream(payload, base_url, api_key, timeout_sec, trace_label)
        except Exception as exc:
            safe_print(f"[LLM_STREAM_FALLBACK] {trace_label} 流式输出失败，改用普通请求：{exc}")
    return _complete_once(payload, base_url, api_key, timeout_sec, trace_label)


def _complete_once(payload: dict[str, Any], base_url: str, api_key: str, timeout_sec: int, trace_label: str) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    safe_print(
        f"[LLM_REQUEST] {trace_label} 请求模型 model={payload.get('model')} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={base_url}"
    )
    start = time.time()
    request = urllib.request.Request(base_url, data=data, headers=build_headers(api_key), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = _decode_response_bytes(response.read(), response)
    except urllib.error.HTTPError as exc:
        body = _decode_response_bytes(exc.read(), exc) if exc.fp else ""
        raise RuntimeError(
            "LLM API HTTP error:\n"
            f"  status={exc.code} {exc.reason}\n"
            f"  url={base_url}\n"
            f"  model={payload.get('model')}\n"
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


def _complete_stream(payload: dict[str, Any], base_url: str, api_key: str, timeout_sec: int, trace_label: str) -> str:
    payload = dict(payload)
    payload["stream"] = True
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    safe_print(
        f"[LLM_REQUEST] {trace_label} 流式请求 model={payload.get('model')} bytes={len(data)} max_tokens={payload.get('max_tokens')} url={base_url}"
    )
    request = urllib.request.Request(base_url, data=data, headers=build_headers(api_key), method="POST")
    chunks: list[str] = []
    printed = 0
    finish_reason: str | None = None
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            for raw_line in response:
                line = _decode_response_bytes(raw_line, response).strip()
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
                content = delta.get("content") or (choice.get("message") or {}).get("content")
                if not content:
                    continue
                chunks.append(repair_mojibake_text(content))
                text = "".join(chunks)
                if len(text) - printed >= 180:
                    safe_print(f"[LLM_STREAM] {trace_label} {text[printed:].replace(chr(10), ' ')}")
                    printed = len(text)
    except urllib.error.HTTPError as exc:
        body = _decode_response_bytes(exc.read(), exc) if exc.fp else ""
        raise RuntimeError(
            "LLM API stream HTTP error:\n"
            f"  status={exc.code} {exc.reason}\n"
            f"  url={base_url}\n"
            f"  model={payload.get('model')}\n"
            f"  request_bytes={len(data)}\n"
            f"  max_tokens={payload.get('max_tokens')}\n"
            f"  response_body={body}"
        ) from exc
    text = repair_mojibake_text("".join(chunks))
    if printed < len(text):
        safe_print(f"[LLM_STREAM] {trace_label} {text[printed:].replace(chr(10), ' ')}")
    if finish_reason == "length":
        raise RuntimeError(
            f"LLM stream output was truncated by max_tokens. trace={trace_label} chars={len(text)} max_tokens={payload.get('max_tokens')}"
        )
    safe_print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f} finish_reason={finish_reason}")
    return text
