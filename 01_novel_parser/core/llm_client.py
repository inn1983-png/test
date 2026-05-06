from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Any


JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


@dataclass
class LLMConfig:
    enabled: bool
    base_url: str
    model: str
    api_key: str
    timeout_sec: int
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            enabled=os.getenv("AI_DRAMA_01_USE_LLM", "0") == "1",
            base_url=os.getenv("AI_DRAMA_LLM_BASE_URL", "http://127.0.0.1:8000/v1/chat/completions"),
            model=os.getenv("AI_DRAMA_LLM_MODEL", "local-model"),
            api_key=os.getenv("AI_DRAMA_LLM_API_KEY", ""),
            timeout_sec=int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "180")),
            temperature=float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", "0.2")),
        )


class LLMClient:
    """Minimal OpenAI-compatible local LLM client.

    Expected endpoint: POST /v1/chat/completions
    The returned assistant content must contain a JSON object.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def is_enabled(self) -> bool:
        return self.config.enabled

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        if not self.config.enabled:
            raise RuntimeError("AI_DRAMA_01_USE_LLM is not enabled")

        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        request = urllib.request.Request(self.config.base_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.config.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        result = json.loads(raw)
        return result["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
        text = self.complete_text(system_prompt, user_prompt)
        return parse_json_from_text(text)


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
    return value
