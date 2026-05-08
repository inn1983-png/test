import json
import subprocess
from pathlib import Path

from backend.app.project_store import ensure_project_dirs
from backend.app.settings_store import load_settings
from backend.app.node_store import list_nodes


def _resolve_video(project_dir, video_path):
    if not video_path:
        return None
    candidate = Path(video_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for base in [project_dir, project_dir / "videos"]:
        path = base / video_path
        if path.exists():
            return path
        path = base / Path(video_path).name
        if path.exists():
            return path
    return None


def _write_manifest(final_dir, data):
    path = final_dir / "final_manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _run_ffmpeg(command):
    return subprocess.run(command, shell=True, check=False, capture_output=True, text=True)


def build(project_id):
    settings = load_settings(project_id)
    project_dir = ensure_project_dirs(project_id)
    final_dir = project_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    resolved = []
    missing = []
    for node in list_nodes(project_id):
        if node.get("video_path"):
            path = _resolve_video(project_dir, node.get("video_path"))
            if path:
                resolved.append(path)
            else:
                missing.append(node.get("video_path"))

    output_path = final_dir / "final.mp4"
    concat_path = final_dir / "concat.txt"
    ffmpeg = settings.get("ffmpeg_path", "ffmpeg")

    if not resolved:
        return _write_manifest(final_dir, {
            "status": "needs_review",
            "output": "final/final.mp4",
            "ffmpeg_path": ffmpeg,
            "video_clips": [],
            "missing": missing,
            "error": "No real video clips found for final assembly."
        })

    concat_lines = []
    for path in resolved:
        safe = str(path).replace("'", "'\\''")
        concat_lines.append("file '" + safe + "'")
    concat_path.write_text("\n".join(concat_lines), encoding="utf-8")

    copy_cmd = f'"{ffmpeg}" -y -f concat -safe 0 -i "{concat_path}" -c copy "{output_path}"'
    result = _run_ffmpeg(copy_cmd)
    if result.returncode != 0:
        transcode_cmd = f'"{ffmpeg}" -y -f concat -safe 0 -i "{concat_path}" -c:v libx264 -c:a aac "{output_path}"'
        result = _run_ffmpeg(transcode_cmd)
        used_command = transcode_cmd
    else:
        used_command = copy_cmd

    if result.returncode != 0 or not output_path.exists():
        return _write_manifest(final_dir, {
            "status": "failed",
            "output": "final/final.mp4",
            "ffmpeg_path": ffmpeg,
            "video_clips": [str(p) for p in resolved],
            "missing": missing,
            "command": used_command,
            "stderr": result.stderr,
            "stdout": result.stdout,
        })

    return _write_manifest(final_dir, {
        "status": "done",
        "output": "final/final.mp4",
        "ffmpeg_path": ffmpeg,
        "video_clips": [str(p) for p in resolved],
        "missing": missing,
        "command": used_command,
    })
