from __future__ import annotations

from pathlib import Path
from typing import Any

from importlib import import_module

artifact_registry = import_module("00_common.artifact_registry")


def resolve_key_output(run_dir: str | Path, module_name: str, artifact_name: str) -> Path | None:
    """Resolve a key output path from manifest.json.

    This is the fastest lookup path for important files like script.json,
    storyboard.json, final_audio.wav, etc.
    """
    run_dir = Path(run_dir)
    manifest = artifact_registry.load_manifest(run_dir)
    key_outputs = manifest.get("key_outputs", {})
    item = key_outputs.get(module_name, {}).get(artifact_name)
    if not item:
        return None

    path = Path(item.get("path", ""))
    if not path:
        return None

    if path.is_absolute():
        return path
    return run_dir / path


def resolve_artifacts(
    run_dir: str | Path,
    module_name: str | None = None,
    artifact_type: str | None = None,
    artifact_name: str | None = None,
    limit: int = 200,
) -> list[Path]:
    """Resolve artifact paths from artifacts.db."""
    run_dir = Path(run_dir)
    rows = artifact_registry.find_artifacts(
        run_dir=run_dir,
        module_name=module_name,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        limit=limit,
    )

    paths: list[Path] = []
    for row in rows:
        path = Path(row.get("path", ""))
        if not path:
            continue
        paths.append(path if path.is_absolute() else run_dir / path)
    return paths


def resolve_required_key_output(run_dir: str | Path, module_name: str, artifact_name: str) -> Path:
    """Resolve a key output or raise a clear error."""
    path = resolve_key_output(run_dir, module_name, artifact_name)
    if path is None:
        raise FileNotFoundError(
            f"Required artifact not found in manifest key_outputs: {module_name}.{artifact_name}"
        )
    if not path.exists():
        raise FileNotFoundError(f"Resolved artifact path does not exist: {path}")
    return path


def resolve_shared_asset(context: dict[str, Any], asset_kind: str, filename: str) -> Path | None:
    """Resolve long-novel shared assets.

    asset_kind examples: characters, scenes, props, voice_library
    """
    shared_assets_dir = context.get("shared_assets_dir") or context.get("runtime", {}).get("shared_assets_dir")
    if not shared_assets_dir:
        return None
    path = Path(shared_assets_dir) / asset_kind / filename
    return path if path.exists() else None


def fallback_module_file(run_dir: str | Path, module_name: str, filename: str) -> Path:
    """Return the conventional module output path.

    This is only a fallback when manifest/db has not been populated yet.
    """
    return Path(run_dir) / module_name / filename
