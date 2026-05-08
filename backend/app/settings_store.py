import json
from backend.app.project_store import ensure_project_dirs, utc_now

DEFAULT_SETTINGS = {
    "comfyui_url": "http://127.0.0.1:8188",
    "image_workflow": "workflows/image/storyboard_image.json",
    "video_workflow": "workflows/video/ltx23_grid_video.json",
    "indextts_command": "",
    "default_voice_id": "default",
    "ffmpeg_path": "ffmpeg",
    "default_grid_mode": "grid_4",
    "default_video_seconds": 12,
    "task_timeout_seconds": 1800,
    "max_retry": 3,
    "wait_until_complete": True,
    "workflow_mappings": {
        "image": {
            "prompt_node": "",
            "prompt_input": "text",
            "negative_node": "",
            "negative_input": "text"
        },
        "video": {
            "prompt_node": "",
            "prompt_input": "text",
            "image_node": "",
            "image_input": "image"
        }
    }
}


def deep_merge(defaults, data):
    result = defaults.copy()
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def settings_path(project_id):
    return ensure_project_dirs(project_id) / "settings.json"


def load_settings(project_id):
    path = settings_path(project_id)
    if not path.exists():
        return save_settings(project_id, DEFAULT_SETTINGS.copy())
    data = json.loads(path.read_text(encoding="utf-8"))
    return deep_merge(DEFAULT_SETTINGS, data)


def save_settings(project_id, settings):
    settings["updated_at"] = utc_now()
    settings_path(project_id).write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return settings
