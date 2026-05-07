from __future__ import annotations

from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")
artifact_resolver = import_module("00_common.artifact_resolver")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS_PATH = ROOT_DIR / "configs" / "module_contracts.json"


def load_contracts(path: str | Path | None = None) -> dict[str, Any]:
    contract_path = Path(path) if path else DEFAULT_CONTRACTS_PATH
    data = io_utils.read_json(contract_path, default={})
    return data if isinstance(data, dict) else {}


def get_module_contract(module_name: str, contracts: dict[str, Any] | None = None) -> dict[str, Any]:
    data = contracts or load_contracts()
    modules = data.get("modules", {})
    if not isinstance(modules, dict):
        return {}
    contract = modules.get(module_name, {})
    return contract if isinstance(contract, dict) else {}


def _resolve_required_file(run_dir: str | Path, required: dict[str, Any]) -> Path | None:
    module_name = required.get("module")
    artifact_name = required.get("name")
    if not isinstance(module_name, str) or not isinstance(artifact_name, str):
        return None

    # 1. manifest key_outputs
    path = artifact_resolver.resolve_key_output(run_dir, module_name, artifact_name)
    if path and path.exists():
        return path

    # 2. artifacts.db
    artifact_paths = artifact_resolver.resolve_artifacts(
        run_dir=run_dir,
        module_name=module_name,
        artifact_name=artifact_name,
        limit=20,
    )
    for artifact_path in artifact_paths:
        if artifact_path.exists():
            return artifact_path

    # 3. conventional module output path fallback
    fallback = artifact_resolver.fallback_module_file(run_dir, module_name, artifact_name)
    if fallback.exists():
        return fallback

    return None


def check_module_requires(
    run_dir: str | Path,
    module_name: str,
    contracts: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Check whether a module's required upstream artifacts exist.

    Contract items may include optional=true. Optional artifacts are reported
    when present, but they do not block the module when missing. This is needed
    for 10_final_assembly, where 09_video/final_video.mp4 and subtitle files are
    preferred inputs, but clips/subtitles can be absent depending on the mode.
    """
    contract = get_module_contract(module_name, contracts)
    requires = contract.get("requires", [])
    if not isinstance(requires, list):
        return False, [f"Invalid requires config for {module_name}: expected list"]

    messages: list[str] = []
    ok = True
    for required in requires:
        if not isinstance(required, dict):
            ok = False
            messages.append(f"Invalid require item for {module_name}: {required!r}")
            continue

        upstream_module = required.get("module")
        artifact_name = required.get("name")
        optional = bool(required.get("optional", False))
        resolved = _resolve_required_file(run_dir, required)
        label = "optional artifact" if optional else "required artifact"
        if resolved is None:
            if optional:
                messages.append(f"Missing optional artifact for {module_name}: {upstream_module}.{artifact_name}")
            else:
                ok = False
                messages.append(f"Missing required artifact for {module_name}: {upstream_module}.{artifact_name}")
        else:
            messages.append(f"Found {label} for {module_name}: {upstream_module}.{artifact_name} -> {resolved}")

    return ok, messages


def describe_contract(module_name: str, contracts: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = get_module_contract(module_name, contracts)
    return {
        "requires": contract.get("requires", []),
        "produces": contract.get("produces", []),
    }
