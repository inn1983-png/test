"""Project filesystem store for Agent Canvas."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "projects"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_project_dirs(project_id: str) -> Path:
    project_dir = PROJECTS_DIR / project_id
    for rel in [
        "source",
        "nodes",
        "assets/characters",
        "assets/scenes",
        "assets/props",
        "assets/voices",
        "assets/styles",
        "images",
        "grids",
        "audio",
        "videos",
        "manifests",
        "history",
        "final",
        "workflows/image",
        "workflows/video",
        "workflows/audio",
        "workflows/grid",
        "workflows/final",
        "workflows/utility",
        "tasks/pending",
        "tasks/running",
        "tasks/done",
        "tasks/failed",
        "tasks/cancelled",
        "tasks/logs",
    ]:
        (project_dir / rel).mkdir(parents=True, exist_ok=True)
    return project_dir


def project_meta_path(project_id: str) -> Path:
    return ensure_project_dirs(project_id) / "project.json"


def load_project(project_id: str) -> dict[str, Any]:
    path = project_meta_path(project_id)
    if not path.exists():
        meta = {
            "project_id": project_id,
            "title": project_id,
            "status": "in_progress",
            "current_stage": "source",
            "progress": 0,
            "failed_tasks": 0,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        save_project(project_id, meta)
        return meta
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(project_id: str, data: dict[str, Any]) -> dict[str, Any]:
    ensure_project_dirs(project_id)
    data["updated_at"] = utc_now()
    project_meta_path(project_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def list_projects() -> list[dict[str, Any]]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for item in sorted(PROJECTS_DIR.iterdir()):
        if item.is_dir():
            projects.append(load_project(item.name))
    return projects
