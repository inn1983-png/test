import json
from pathlib import Path

from backend.app.project_store import ROOT
from backend.app.settings_store import load_settings


def resolve_configured_path(value):
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    return ROOT / path


def indextts_root(project_id):
    settings = load_settings(project_id)
    return resolve_configured_path(settings.get("indextts_root", "index-tts"))


def voice_index_path(project_id):
    settings = load_settings(project_id)
    root = indextts_root(project_id)
    value = settings.get("indextts_voice_index", "examples/voice_index.json")
    path = Path(str(value or ""))
    return path if path.is_absolute() else root / path


def load_voice_index(project_id):
    path = voice_index_path(project_id)
    if not path.exists():
        return {}, path
    return json.loads(path.read_text(encoding="utf-8")), path


def list_indextts_voices(project_id, limit=None):
    data, path = load_voice_index(project_id)
    voices = []
    for voice_id, info in sorted(data.items()):
        entries = info.get("entries") or []
        first = entries[0] if entries else {}
        entry_id = first.get("entry_id") or voice_id
        voices.append({
            "voice_id": voice_id,
            "speaker_name": info.get("speaker_name", voice_id),
            "gender": info.get("gender", ""),
            "age": info.get("age", ""),
            "category": info.get("category", ""),
            "sample_text": first.get("text", ""),
            "duration": first.get("duration"),
            "voice_file": "examples/" + entry_id + ".wav",
        })
        if limit and len(voices) >= limit:
            break
    return {
        "configured": path.exists(),
        "voice_index": str(path),
        "voice_count": len(data),
        "voices": voices,
    }


def resolve_voice_file(project_id, voice_id=None):
    settings = load_settings(project_id)
    root = indextts_root(project_id)
    selected_id = voice_id or settings.get("default_voice_id") or "default"
    data, _ = load_voice_index(project_id)
    if selected_id not in data and selected_id == "default" and data:
        selected_id = sorted(data.keys())[0]
    info = data.get(selected_id, {})
    entries = info.get("entries") or []
    entry_id = (entries[0] or {}).get("entry_id") if entries else selected_id
    voice_file = root / "examples" / (str(entry_id) + ".wav")
    return {
        "voice_id": selected_id,
        "voice_file": str(voice_file),
        "voice_file_exists": voice_file.exists(),
        "speaker_name": info.get("speaker_name", selected_id),
    }
