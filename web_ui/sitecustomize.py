from __future__ import annotations

"""Web UI server hook.

server.py is a long file. To avoid overwriting it, this sitecustomize hook patches
its Handler class when the class is created and patches build_command after
server.py imports are complete.

Adds:
- POST /api/review/rewrite  -> call LLM to generate reviewed JSON, preview only
- POST /api/review/apply    -> apply reviewed JSON over official module output
- build_command support for payload.to_module -> --to-module
- build_command support for payload.style_preset -> AI_DRAMA_STYLE_PRESET
"""

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import http.server

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_ORIGINAL_INIT_SUBCLASS = getattr(http.server.SimpleHTTPRequestHandler, "__init_subclass__", None)


def _read_json_body(handler: http.server.SimpleHTTPRequestHandler) -> dict[str, Any]:
    if hasattr(handler, "read_body_json"):
        value = handler.read_body_json()
        return value if isinstance(value, dict) else {}
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _send_json(handler: http.server.SimpleHTTPRequestHandler, data: dict[str, Any], status: int = 200) -> None:
    if hasattr(handler, "send_json"):
        handler.send_json(data, status=status)
        return
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _patch_build_command(globals_dict: dict[str, Any]) -> None:
    original = globals_dict.get("build_command")
    if not callable(original) or getattr(original, "__ui_patch_applied__", False):
        return

    def build_command(payload: dict[str, Any], run_dir: Path):
        cmd, env, kind = original(payload, run_dir)
        to_module = str(payload.get("to_module") or "").strip()
        if to_module and "--to-module" not in cmd:
            cmd.extend(["--to-module", to_module])

        style_preset = str(payload.get("style_preset") or "").strip()
        if style_preset:
            env["AI_DRAMA_STYLE_PRESET"] = style_preset
            env["AI_DRAMA_SELECTED_STYLE_PRESET"] = style_preset

        return cmd, env, kind

    build_command.__ui_patch_applied__ = True
    globals_dict["build_command"] = build_command


def _patch_handler(handler_cls: type) -> None:
    if getattr(handler_cls, "__review_rewrite_api_patched__", False):
        return

    original_do_post = getattr(handler_cls, "do_POST", None)

    # The Handler.__init__ method is inherited from socketserver and does NOT
    # point to server.py globals. The do_POST function is defined inside
    # server.py, so its __globals__ is the correct namespace for build_command.
    try:
        if callable(original_do_post) and hasattr(original_do_post, "__globals__"):
            _patch_build_command(original_do_post.__globals__)
    except Exception:
        pass

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/review/rewrite":
            try:
                payload = _read_json_body(self)
                result_rewriter = __import__("importlib").import_module("00_common.result_rewriter")
                result = result_rewriter.rewrite_module_result(
                    run_dir_raw=str(payload.get("run_dir") or ""),
                    module_name=str(payload.get("module_name") or payload.get("module") or ""),
                    user_note=str(payload.get("user_note") or payload.get("note") or ""),
                )
                return _send_json(self, result, status=200)
            except Exception as exc:
                return _send_json(self, {"status": "failed", "error": str(exc)}, status=500)

        if parsed.path == "/api/review/apply":
            try:
                payload = _read_json_body(self)
                result_rewriter = __import__("importlib").import_module("00_common.result_rewriter")
                result = result_rewriter.apply_reviewed_result(
                    run_dir_raw=str(payload.get("run_dir") or ""),
                    module_name=str(payload.get("module_name") or payload.get("module") or ""),
                    reviewed_path_raw=str(payload.get("reviewed_path") or ""),
                )
                return _send_json(self, result, status=200)
            except Exception as exc:
                return _send_json(self, {"status": "failed", "error": str(exc)}, status=500)

        if original_do_post:
            return original_do_post(self)
        return _send_json(self, {"error": "POST endpoint not found"}, status=404)

    handler_cls.do_POST = do_POST
    handler_cls.__review_rewrite_api_patched__ = True


def _init_subclass(cls, **kwargs):
    if _ORIGINAL_INIT_SUBCLASS:
        try:
            _ORIGINAL_INIT_SUBCLASS(**kwargs)
        except TypeError:
            pass
    if cls.__name__ == "Handler":
        _patch_handler(cls)


http.server.SimpleHTTPRequestHandler.__init_subclass__ = classmethod(_init_subclass)
