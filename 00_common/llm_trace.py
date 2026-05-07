from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

RAW_RESPONSE_LIMIT = 200_000
JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "llm_trace")).strip("._")
    return text or "llm_trace"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_json_object_from_text(text: str, repair_text: Callable[[str], str] | None = None) -> dict[str, Any]:
    stripped = repair_text(text).strip() if repair_text else str(text or "").strip()
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
    return value


class LLMTrace:
    def __init__(self, output_dir: str | Path | None, trace_label: str) -> None:
        self.enabled = output_dir is not None
        self.path = Path(output_dir) / "llm_traces" / _safe_name(trace_label) if output_dir is not None else None

    def write_request(self, data: dict[str, Any]) -> None:
        if not self.enabled or self.path is None:
            return
        request = dict(data)
        request.pop("api_key", None)
        request.pop("authorization", None)
        request["created_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(self.path / "request.json", request)

    def write_raw_response(self, text: str) -> None:
        if not self.enabled or self.path is None:
            return
        raw = str(text or "")
        suffix = "" if len(raw) <= RAW_RESPONSE_LIMIT else f"\n\n[TRUNCATED raw_response chars={len(raw)} limit={RAW_RESPONSE_LIMIT}]"
        _write_text(self.path / "raw_response.txt", raw[:RAW_RESPONSE_LIMIT] + suffix)

    def write_parsed_before_clean(self, data: dict[str, Any]) -> None:
        if self.enabled and self.path is not None:
            _write_json(self.path / "parsed_before_clean.json", data)

    def write_parsed_after_clean(self, data: dict[str, Any]) -> None:
        if self.enabled and self.path is not None:
            _write_json(self.path / "parsed_after_clean.json", data)

    def write_repair_request(self, broken_text: str, error: str) -> None:
        if not self.enabled or self.path is None:
            return
        _write_json(
            self.path / "repair_request.json",
            {
                "error": error,
                "broken_text_preview": str(broken_text or "")[:RAW_RESPONSE_LIMIT],
                "broken_text_truncated": len(str(broken_text or "")) > RAW_RESPONSE_LIMIT,
            },
        )

    def write_repair_response(self, data: Any) -> None:
        if not self.enabled or self.path is None:
            return
        text = json.dumps(data, ensure_ascii=False, indent=2) if not isinstance(data, str) else data
        _write_text(self.path / "repair_response.txt", text[:RAW_RESPONSE_LIMIT])

    def write_final_stage_output(self, data: dict[str, Any]) -> None:
        if self.enabled and self.path is not None:
            _write_json(self.path / "final_stage_output.json", data)


def start_trace(output_dir: str | Path | None, trace_label: str) -> LLMTrace:
    return LLMTrace(output_dir, trace_label)
