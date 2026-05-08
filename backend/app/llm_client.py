import json
import http.client
import urllib.error
from urllib.parse import urlparse
from pathlib import Path

from backend.app.settings_store import load_settings


def _request_json(url, payload=None, timeout=10):
    parsed = urlparse(url)
    connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    conn = connection_cls(parsed.hostname, parsed.port, timeout=timeout)
    body = None
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    conn.request("POST" if body is not None else "GET", path, body=body, headers=headers)
    resp = conn.getresponse()
    text = resp.read().decode("utf-8")
    conn.close()
    if resp.status >= 400:
        raise RuntimeError("HTTP " + str(resp.status) + ": " + text)
    return json.loads(text) if text else {}


def llm_config(project_id):
    settings = load_settings(project_id)
    return {
        "provider": settings.get("llm_provider", "llama_cpp"),
        "base_url": str(settings.get("llm_base_url", "http://127.0.0.1:8080/v1")).rstrip("/"),
        "model": settings.get("llm_model", "gemma-4-31B-it-Q4_K_M"),
        "llama_cpp_root": settings.get("llama_cpp_root", ""),
        "llama_cpp_server_exe": settings.get("llama_cpp_server_exe", ""),
        "llama_cpp_model_path": settings.get("llama_cpp_model_path", ""),
        "llama_cpp_mmproj_path": settings.get("llama_cpp_mmproj_path", ""),
        "llama_cpp_context_size": settings.get("llama_cpp_context_size", 49152),
        "llama_cpp_gpu_layers": settings.get("llama_cpp_gpu_layers", 99),
        "llama_cpp_port": settings.get("llama_cpp_port", 8080),
    }


def check_llm(project_id):
    config = llm_config(project_id)
    local_paths = {}
    for key in ["llama_cpp_root", "llama_cpp_server_exe", "llama_cpp_model_path", "llama_cpp_mmproj_path"]:
        value = config.get(key) or ""
        local_paths[key] = {"path": value, "exists": bool(value) and Path(value).exists()}

    result = {
        "check": "llm",
        "provider": config["provider"],
        "base_url": config["base_url"],
        "model": config["model"],
        "local_paths": local_paths,
        "context_rule": "Only prompts sent by this application affect the local model; this Codex chat is not sent unless code explicitly includes it.",
    }

    try:
        models = _request_json(config["base_url"] + "/models", timeout=5)
        result.update({"ok": True, "status": "server_ready", "models": models})
    except urllib.error.URLError as exc:
        result.update({"ok": False, "status": "server_not_reachable", "error": str(exc)})
    except Exception as exc:
        result.update({"ok": False, "status": "failed", "error": str(exc)})
    return result


def chat_once(project_id, system_prompt, user_prompt, max_tokens=512, temperature=0.7):
    config = llm_config(project_id)
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    return _request_json(config["base_url"] + "/chat/completions", payload=payload, timeout=120)
