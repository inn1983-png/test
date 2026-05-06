from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")


def manifest_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / "manifest.json"


def load_manifest(run_dir: str | Path) -> dict[str, Any]:
    return io_utils.read_json(manifest_path(run_dir), default={"artifacts": []})


def save_manifest(run_dir: str | Path, manifest: dict[str, Any]) -> None:
    io_utils.write_json(manifest_path(run_dir), manifest)


def register_artifact(
    run_dir: str | Path,
    module_name: str,
    artifact_name: str,
    path: str | Path,
    artifact_type: str,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register a module output artifact for later modules.

    This keeps the project/chapter run inspectable without scanning folders.
    """
    run_dir = Path(run_dir)
    target = Path(path)
    try:
        rel_path = str(target.relative_to(run_dir))
    except ValueError:
        rel_path = str(target)

    manifest = load_manifest(run_dir)
    artifacts = manifest.setdefault("artifacts", [])

    artifacts.append(
        {
            "module": module_name,
            "name": artifact_name,
            "type": artifact_type,
            "path": rel_path,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )

    save_manifest(run_dir, manifest)


def find_artifacts(run_dir: str | Path, module_name: str | None = None, artifact_type: str | None = None) -> list[dict[str, Any]]:
    manifest = load_manifest(run_dir)
    artifacts = manifest.get("artifacts", [])

    result = []
    for item in artifacts:
        if module_name and item.get("module") != module_name:
            continue
        if artifact_type and item.get("type") != artifact_type:
            continue
        result.append(item)
    return result
