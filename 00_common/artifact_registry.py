from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")
artifact_db = import_module("00_common.artifact_db")


def manifest_path(run_dir: str | Path) -> Path:
    return Path(run_dir) / "manifest.json"


def load_manifest(run_dir: str | Path) -> dict[str, Any]:
    return io_utils.read_json(
        manifest_path(run_dir),
        default={
            "artifact_store": "artifacts.db",
            "artifact_summary": {
                "total": 0,
                "by_module": {},
                "by_type": {},
            },
            "key_outputs": {},
        },
    )


def save_manifest(run_dir: str | Path, manifest: dict[str, Any]) -> None:
    io_utils.write_json(manifest_path(run_dir), manifest)


def refresh_manifest_summary(run_dir: str | Path) -> None:
    manifest = load_manifest(run_dir)
    manifest["artifact_store"] = "artifacts.db"
    manifest["artifact_summary"] = {
        "total": artifact_db.count_artifacts(run_dir),
        "by_module": artifact_db.count_by_module(run_dir),
        "by_type": artifact_db.count_by_type(run_dir),
    }
    manifest.setdefault("key_outputs", {})
    save_manifest(run_dir, manifest)


def register_artifact(
    run_dir: str | Path,
    module_name: str,
    artifact_name: str,
    path: str | Path,
    artifact_type: str,
    description: str = "",
    metadata: dict[str, Any] | None = None,
    is_key_output: bool = False,
) -> None:
    """Register an artifact.

    Detailed rows are stored in artifacts.db.
    manifest.json remains a lightweight summary and key-output index.
    """
    artifact_db.register_artifact(
        run_dir=run_dir,
        module_name=module_name,
        artifact_name=artifact_name,
        path=path,
        artifact_type=artifact_type,
        description=description,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )

    manifest = load_manifest(run_dir)
    if is_key_output:
        run_path = Path(run_dir)
        target = Path(path)
        try:
            rel_path = str(target.relative_to(run_path))
        except ValueError:
            rel_path = str(target)
        manifest.setdefault("key_outputs", {}).setdefault(module_name, {})[artifact_name] = {
            "type": artifact_type,
            "path": rel_path,
            "description": description,
        }
        save_manifest(run_dir, manifest)

    refresh_manifest_summary(run_dir)


def find_artifacts(
    run_dir: str | Path,
    module_name: str | None = None,
    artifact_type: str | None = None,
    artifact_name: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    return artifact_db.find_artifacts(
        run_dir=run_dir,
        module_name=module_name,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        limit=limit,
    )
