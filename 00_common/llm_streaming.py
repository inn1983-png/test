from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


def stream_log_enabled() -> bool:
    return os.getenv("AI_DRAMA_LLM_STREAM_LOG", "1").strip().lower() not in {"0", "false", "no"}


def build_headers(api_key: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


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
    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if stream_log_enabled():
        try:
            return _complete_stream(payload, base_url, api_key, timeout_sec, trace_label)
        except Exception as exc:
            print(f"[LLM_STREAM_FALLBACK] {trace_label} 流式输出失败，改用普通请求：{exc}", flush=True)
    return _complete_once(payload, base_url, api_key, timeout_sec, trace_label)


def _complete_once(payload: dict[str, Any], base_url: str, api_key: str, timeout_sec: int, trace_label: str) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    print(f"[LLM_REQUEST] {trace_label} 请求模型 bytes={len(data)} url={base_url}", flush=True)
    start = time.time()
    request = urllib.request.Request(base_url, data=data, headers=build_headers(api_key), method="POST")
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        raw = response.read().decode("utf-8")
    result = json.loads(raw)
    text = result["choices"][0]["message"]["content"]
    print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f}", flush=True)
    print(f"[LLM_OUTPUT_PREVIEW] {trace_label} {text[:1200].replace(chr(10), ' ')}", flush=True)
    return text


def _complete_stream(payload: dict[str, Any], base_url: str, api_key: str, timeout_sec: int, trace_label: str) -> str:
    payload = dict(payload)
    payload["stream"] = True
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    print(f"[LLM_REQUEST] {trace_label} 流式请求 bytes={len(data)} url={base_url}", flush=True)
    request = urllib.request.Request(base_url, data=data, headers=build_headers(api_key), method="POST")
    chunks: list[str] = []
    printed = 0
    start = time.time()
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
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
            content = delta.get("content") or (choice.get("message") or {}).get("content")
            if not content:
                continue
            chunks.append(content)
            text = "".join(chunks)
            if len(text) - printed >= 180:
                print(f"[LLM_STREAM] {trace_label} {text[printed:].replace(chr(10), ' ')}", flush=True)
                printed = len(text)
    text = "".join(chunks)
    if printed < len(text):
        print(f"[LLM_STREAM] {trace_label} {text[printed:].replace(chr(10), ' ')}", flush=True)
    print(f"[LLM_DONE] {trace_label} 输出完成 chars={len(text)} seconds={time.time() - start:.1f}", flush=True)
    return text
