from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

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
        return cls(base_url=base_url, model=model, api_key=os.getenv("AI_DRAMA_LLM_API_KEY", ""), timeout_sec=int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "180")), temperature=float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", "0.2")))


class LLMClient:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {"model": self.config.model, "temperature": self.config.temperature, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(self.config.base_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        result = json.loads(raw)
        return result["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any], repair_callback: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
        text = self.complete_text(system_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))
        try:
            return parse_json_from_text(text)
        except Exception as exc:
            if repair_callback is None:
                raise
            return repair_callback(text, str(exc))


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
    return value
