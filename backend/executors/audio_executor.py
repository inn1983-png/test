from backend.app.node_store import load_node, update_node
from backend.app.settings_store import load_settings


def run(project_id, node_id):
    node = load_node(project_id, node_id)
    settings = load_settings(project_id)
    audio_path = "audio/" + node_id + ".wav"
    subtitle_path = "audio/" + node_id + ".srt"
    command = settings.get("cosyvoice2_command", "")
    return update_node(project_id, node_id, {
        "status": "done" if command else "needs_review",
        "audio_path": audio_path,
        "subtitle_path": subtitle_path,
        "audio_text": node.get("content") or node.get("dialogue_text") or node.get("cap") or "",
        "cosyvoice2_command_configured": bool(command),
        "executor_note": "CosyVoice2 local command/path is reserved in settings and must be configured locally.",
    })
