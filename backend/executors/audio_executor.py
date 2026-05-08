import subprocess
from pathlib import Path

from backend.app.node_store import load_node, update_node
from backend.app.project_store import ensure_project_dirs
from backend.app.settings_store import load_settings
from backend.app.indextts_voice_store import indextts_root, resolve_voice_file


def _audio_text(node):
    if node.get("audio_text"):
        return node["audio_text"]
    if node.get("dialogue_text"):
        return node["dialogue_text"]
    if isinstance(node.get("os"), list):
        return "\n".join(str(x) for x in node["os"])
    return node.get("content") or node.get("cap") or ""


def _format_command(template, project_dir, text_file, output_file, text, voice_id, voice_file, root):
    return template.format(
        project_dir=str(project_dir),
        text_file=str(text_file),
        output_file=str(output_file),
        text=text.replace('"', '\\"'),
        voice_id=voice_id,
        voice_file=str(voice_file),
        indextts_root=str(root),
    )


def run(project_id, node_id):
    project_dir = ensure_project_dirs(project_id)
    node = load_node(project_id, node_id)
    settings = load_settings(project_id)
    command_template = settings.get("indextts_command", "")
    voice_id = node.get("voice_id") or settings.get("narrator_voice_id") or settings.get("default_voice_id", "voice_06")
    voice = resolve_voice_file(project_id, voice_id)
    root = indextts_root(project_id)
    text = _audio_text(node)

    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    text_file = audio_dir / (node_id + ".txt")
    output_file = audio_dir / (node_id + ".wav")
    subtitle_file = audio_dir / (node_id + ".srt")
    text_file.write_text(text, encoding="utf-8")

    if not command_template:
        return update_node(project_id, node_id, {
            "status": "needs_review",
            "audio_text": text,
            "audio_text_file": "audio/" + text_file.name,
            "audio_path": "audio/" + output_file.name,
            "subtitle_path": "audio/" + subtitle_file.name,
            "indextts_command_configured": False,
            "voice_file": voice["voice_file"],
            "voice_file_exists": voice["voice_file_exists"],
            "executor_note": "Set indextts_command in Settings. Supported placeholders: {text}, {text_file}, {output_file}, {voice_id}, {voice_file}, {project_dir}, {indextts_root}",
        })

    command = _format_command(command_template, project_dir, text_file, output_file, text, voice_id, voice["voice_file"], root)
    try:
        completed = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)
    except Exception as exc:
        return update_node(project_id, node_id, {"status": "failed", "error": str(exc)})

    if completed.returncode != 0:
        return update_node(project_id, node_id, {
            "status": "failed",
            "error": completed.stderr or completed.stdout or "IndexTTS command failed",
            "indextts_command": command,
        })

    if not output_file.exists():
        return update_node(project_id, node_id, {
            "status": "needs_review",
            "error": "IndexTTS command finished but output wav was not found.",
            "indextts_command": command,
            "expected_output": "audio/" + output_file.name,
        })

    return update_node(project_id, node_id, {
        "status": "done",
        "audio_text": text,
        "audio_text_file": "audio/" + text_file.name,
        "audio_path": "audio/" + output_file.name,
        "subtitle_path": "audio/" + subtitle_file.name,
        "voice_id": voice_id,
        "voice_file": voice["voice_file"],
        "indextts_command_configured": True,
    })
