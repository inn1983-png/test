import json

from backend.app.project_store import ensure_project_dirs
from backend.app.settings_store import load_settings
from backend.app.node_store import list_nodes


def build(project_id):
    settings = load_settings(project_id)
    final_dir = ensure_project_dirs(project_id) / "final"
    videos = []
    for node in list_nodes(project_id):
        if node.get("video_path"):
            videos.append(node.get("video_path"))
    data = {
        "status": "ready_for_local_assembly" if videos else "waiting_video_clips",
        "output": "final/final.mp4",
        "ffmpeg_path": settings.get("ffmpeg_path", "ffmpeg"),
        "video_clips": videos,
        "note": "FFmpeg path is reserved in settings. Fill local path in UI Settings."
    }
    path = final_dir / "final_manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
