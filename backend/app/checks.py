import json
import shlex
import subprocess

from backend.app.project_store import ensure_project_dirs
from backend.app.settings_store import load_settings
from backend.app.indextts_voice_store import indextts_root, list_indextts_voices, resolve_voice_file
from backend.app.llm_client import check_llm
from backend.executors.comfyui_client import ping


def _command_parts(command):
    parts = shlex.split(str(command), posix=False)
    return [part.strip('"') for part in parts if part.strip()]


def check_comfyui(project_id):
    result = ping(project_id)
    ok = isinstance(result, dict) and "error" not in result
    return {
        "check": "comfyui-ping",
        "ok": ok,
        "status": "success" if ok else "failed",
        "result": result,
    }


def check_ffmpeg(project_id):
    settings = load_settings(project_id)
    ffmpeg = str(settings.get("ffmpeg_path") or "").strip()
    if not ffmpeg:
        return {"check": "ffmpeg", "ok": False, "status": "not_configured", "error": "ffmpeg_path is empty"}
    try:
        command = _command_parts(ffmpeg) + ["-version"]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return {"check": "ffmpeg", "ok": False, "status": "failed", "ffmpeg_path": ffmpeg, "error": str(exc)}
    first_line = (completed.stdout or completed.stderr or "").splitlines()
    return {
        "check": "ffmpeg",
        "ok": completed.returncode == 0,
        "status": "success" if completed.returncode == 0 else "failed",
        "ffmpeg_path": ffmpeg,
        "stdout_first_line": first_line[0] if first_line else "",
        "stderr": completed.stderr,
    }


def check_indextts_command(project_id):
    settings = load_settings(project_id)
    command_template = str(settings.get("indextts_command") or "").strip()
    project_dir = ensure_project_dirs(project_id)
    audio_dir = project_dir / "audio"
    text_file = audio_dir / "indextts_check.txt"
    output_file = audio_dir / "indextts_check.wav"
    root = indextts_root(project_id)
    voice = resolve_voice_file(project_id, settings.get("narrator_voice_id") or settings.get("default_voice_id"))

    if not command_template:
        return {
            "check": "indextts-command",
            "ok": False,
            "status": "not_configured",
            "configured": False,
            "discovered_root": str(root) if root.exists() else "",
            "voice": voice,
            "message": "Set indextts_command in Settings before running audio generation.",
            "placeholders": ["{text}", "{text_file}", "{output_file}", "{voice_id}", "{voice_file}", "{project_dir}", "{indextts_root}"],
        }

    try:
        preview = command_template.format(
            project_dir=str(project_dir),
            text_file=str(text_file),
            output_file=str(output_file),
            text="短测试",
            voice_id=settings.get("narrator_voice_id") or settings.get("default_voice_id", "voice_06"),
            voice_file=voice["voice_file"],
            indextts_root=str(root),
        )
    except Exception as exc:
        return {
            "check": "indextts-command",
            "ok": False,
            "status": "invalid_template",
            "configured": True,
            "error": str(exc),
        }

    return {
        "check": "indextts-command",
        "ok": True,
        "status": "configured",
        "configured": True,
        "dry_run_command": preview,
        "safe_execution": "skipped",
        "discovered_root": str(root) if root.exists() else "",
        "voice": voice,
    }


def validate_workflow_json(content):
    if isinstance(content, dict):
        return {"check": "workflow-json", "ok": True, "status": "valid"}
    try:
        json.loads(str(content or ""))
    except Exception as exc:
        return {"check": "workflow-json", "ok": False, "status": "invalid", "error": str(exc)}
    return {"check": "workflow-json", "ok": True, "status": "valid"}


def run_check(project_id, check_name, body=None):
    if check_name == "comfyui-ping":
        return check_comfyui(project_id)
    if check_name == "ffmpeg":
        return check_ffmpeg(project_id)
    if check_name == "indextts":
        return check_indextts_command(project_id)
    if check_name == "indextts-voices":
        return list_indextts_voices(project_id, limit=200)
    if check_name == "llm":
        return check_llm(project_id)
    if check_name == "workflow-json":
        return validate_workflow_json((body or {}).get("content", ""))
    raise ValueError("unknown check: " + check_name)
