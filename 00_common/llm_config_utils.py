from __future__ import annotations

import logging
import os

_logger = logging.getLogger(__name__)

CLOUD_DEFAULT_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
CLOUD_DEFAULT_MODEL = "deepseek-v4-flash"
LEGACY_DEFAULT_MODELS = {"deepseek-v4-pro", "deepseek-v4", "deepseek-pro"}


def is_local_base_url(base_url: str) -> bool:
    if not base_url:
        return False
    lower = base_url.lower()
    return any(h in lower for h in ("127.0.0.1", "localhost", "::1", "0.0.0.0"))


def validate_api_key_requirement(base_url: str, api_key: str, module_name: str) -> None:
    if api_key:
        return
    if is_local_base_url(base_url):
        return
    if base_url == CLOUD_DEFAULT_BASE_URL or base_url.startswith("https://api."):
        _logger.warning(
            "%s 当前使用云端 LLM 但未设置 AI_DRAMA_LLM_API_KEY，请求可能失败；"
            "如使用本地模型，请设置 AI_DRAMA_LLM_BASE_URL 和 AI_DRAMA_LLM_MODEL。",
            module_name,
        )


def resolve_llm_base_url(env_default: str) -> str:
    return os.getenv("AI_DRAMA_LLM_BASE_URL", env_default).strip()


def resolve_llm_model(env_default: str) -> str:
    """Resolve text LLM model for 01-06.

    Existing module files may still pass old defaults such as deepseek-v4-pro.
    When AI_DRAMA_LLM_MODEL is not explicitly set, normalize those legacy
    defaults to the current project default: DeepSeek Flash.
    """
    env_model = os.getenv("AI_DRAMA_LLM_MODEL", "").strip()
    if env_model:
        return env_model
    default_model = (env_default or "").strip()
    if default_model in LEGACY_DEFAULT_MODELS:
        return CLOUD_DEFAULT_MODEL
    return default_model or CLOUD_DEFAULT_MODEL


def resolve_llm_api_key() -> str:
    return os.getenv("AI_DRAMA_LLM_API_KEY", "").strip()


def resolve_llm_timeout(default: int = 6000) -> int:
    return int(os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", str(default)))


def resolve_llm_temperature(default: float = 0.1) -> float:
    return float(os.getenv("AI_DRAMA_LLM_TEMPERATURE", str(default)))
