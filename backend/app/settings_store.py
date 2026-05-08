import json
from backend.app.project_store import ensure_project_dirs, utc_now

DEFAULT_SETTINGS = {
    "comfyui_url": "http://127.0.0.1:8188",
    "image_workflow": "workflows/image_storyboard.json",
    "video_workflow": "workflows/ltx23_grid_video.json",
    "cosyvoice2_command": "",
    "ffmpeg_path": "ffmpeg",
    "default_grid_mode": "grid_4",
    "default_video_seconds": 12,
    "task_timeout_seconds": 1800,
    "max_retry": 3,
    "wait_until_complete": True
}


def settings_path(project_id):
    return ensure_project_dirs(project_id) / "settings.json"


def load_settings(project_id):
    path = settings_path(project_id)
    if not path.exists():
        return save_settings(project_id, DEFAULT_SETTINGS.copy())
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    return merged


def save_settings(project_id, settings):
    settings["updated_at"] = utc_now()
    settings_path(project_id).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return settings
