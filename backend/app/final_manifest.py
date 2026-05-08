import json

from backend.app.project_store import ensure_project_dirs


def final_manifest_path(project_id):
    return ensure_project_dirs(project_id) / "final" / "final_manifest.json"


def final_video_path(project_id):
    return ensure_project_dirs(project_id) / "final" / "final.mp4"


def load_final_manifest(project_id):
    path = final_manifest_path(project_id)
    video_path = final_video_path(project_id)
    if not path.exists():
        return {
            "exists": False,
            "status": "missing",
            "path": "final/final_manifest.json",
            "final_file_exists": video_path.exists(),
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data["exists"] = True
    data["path"] = "final/final_manifest.json"
    data["final_file_exists"] = video_path.exists()
    if video_path.exists():
        data["video_url"] = "/api/projects/{project_id}/final-video".format(project_id=project_id)
    return data
