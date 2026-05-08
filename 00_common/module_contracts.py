from __future__ import annotations

from pathlib import Path
from typing import Any

from importlib import import_module

io_utils = import_module("00_common.io_utils")
artifact_resolver = import_module("00_common.artifact_resolver")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS_PATH = ROOT_DIR / "configs" / "module_contracts.json"

# Used by UI/API requirement inspection when a user tries to run a single module
# without its upstream artifacts. Keep this list aligned with pipeline.json.
RECOMMENDED_START_MODULES = {
    "00_style_system": "00_style_system",
    "01_novel_parser": "01_novel_parser",
    "02_script_writer": "02_script_writer",
    "03_character_system": "03_character_system",
    "04_scene_system": "04_scene_system",
    "05_prop_system": "05_prop_system",
    "06_storyboard": "06_storyboard",
    "07_storyboard_image": "07_storyboard_image",
    "08_audio": "08_audio",
    "09_video": "09_video",
    "10_final_assembly": "10_final_assembly",
}
RECOMMENDED_ORDER = [
    "00_style_system",
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly",
]


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


def _candidate_artifact_paths(run_dir: str | Path, item: dict[str, Any], default_module: str) -> list[Path]:
    module_name = item.get("module") or default_module
    artifact_name = item.get("name")
    if not isinstance(module_name, str) or not isinstance(artifact_name, str):
        return []

    candidates: list[Path] = []

    key_output = artifact_resolver.resolve_key_output(run_dir, module_name, artifact_name)
    if key_output:
        candidates.append(key_output)

    artifact_paths = artifact_resolver.resolve_artifacts(
        run_dir=run_dir,
        module_name=module_name,
        artifact_name=artifact_name,
        limit=20,
    )
    candidates.extend(artifact_paths)
    candidates.append(artifact_resolver.fallback_module_file(run_dir, module_name, artifact_name))

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def _directory_has_file(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(child.is_file() for child in path.rglob("*"))


def _artifact_exists_for_type(path: Path, artifact_type: str) -> bool:
    if artifact_type in {"video_dir", "image_dir", "audio_dir"}:
        return _directory_has_file(path)
    return path.is_file()


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


def _expected_artifact_path(run_dir: str | Path, module_name: str, artifact_name: str) -> Path:
    return artifact_resolver.fallback_module_file(run_dir, module_name, artifact_name)


def _recommend_from_missing(missing_requires: list[dict[str, Any]], default_module: str) -> str:
    candidates: list[str] = []
    for item in missing_requires:
        upstream = item.get("module")
        if isinstance(upstream, str):
            candidates.append(RECOMMENDED_START_MODULES.get(upstream, upstream))
    if not candidates:
        return default_module

    order = {module: index for index, module in enumerate(RECOMMENDED_ORDER)}
    return min(candidates, key=lambda module: order.get(module, len(order)))


def inspect_module_requirements(
    run_dir: str | Path,
    module_name: str,
    contracts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return structured dependency details for a single-module run decision."""
    contract = get_module_contract(module_name, contracts)
    requires = contract.get("requires", [])
    available_requires: list[dict[str, Any]] = []
    missing_requires: list[dict[str, Any]] = []
    missing_optional_requires: list[dict[str, Any]] = []
    messages: list[str] = []

    if not contract:
        return {
            "module": module_name,
            "can_run": False,
            "missing_requires": [{"module": module_name, "name": None, "message": "module contract not found"}],
            "available_requires": [],
            "missing_optional_requires": [],
            "recommended_action": "run_from_module",
            "recommended_from_module": module_name,
            "messages": [f"Module contract not found: {module_name}"],
        }

    if not isinstance(requires, list):
        return {
            "module": module_name,
            "can_run": False,
            "missing_requires": [{"module": module_name, "name": None, "message": "invalid requires config"}],
            "available_requires": [],
            "missing_optional_requires": [],
            "recommended_action": "run_from_module",
            "recommended_from_module": module_name,
            "messages": [f"Invalid requires config for {module_name}: expected list"],
        }

    for required in requires:
        if not isinstance(required, dict):
            missing_requires.append({"module": module_name, "name": None, "message": f"invalid require item: {required!r}"})
            continue

        upstream_module = required.get("module")
        artifact_name = required.get("name")
        artifact_type = required.get("type")
        optional = bool(required.get("optional", False))
        expected_path = (
            _expected_artifact_path(run_dir, upstream_module, artifact_name)
            if isinstance(upstream_module, str) and isinstance(artifact_name, str)
            else None
        )
        base_item = {
            "module": upstream_module,
            "name": artifact_name,
            "type": artifact_type,
            "optional": optional,
            "expected_path": str(expected_path) if expected_path else None,
        }
        resolved = _resolve_required_file(run_dir, required)
        if resolved is not None:
            item = {**base_item, "path": str(resolved)}
            available_requires.append(item)
            messages.append(f"Found required artifact for {module_name}: {upstream_module}.{artifact_name} -> {resolved}")
        elif optional:
            item = {**base_item, "message": "missing optional upstream artifact"}
            missing_optional_requires.append(item)
            messages.append(f"Missing optional artifact for {module_name}: {upstream_module}.{artifact_name}")
        else:
            item = {**base_item, "message": "missing required upstream artifact"}
            missing_requires.append(item)
            messages.append(f"Missing required artifact for {module_name}: {upstream_module}.{artifact_name}")

    can_run = not missing_requires
    recommended_from_module = module_name if can_run else _recommend_from_missing(missing_requires, module_name)
    return {
        "module": module_name,
        "can_run": can_run,
        "missing_requires": missing_requires,
        "available_requires": available_requires,
        "missing_optional_requires": missing_optional_requires,
        "recommended_action": "run_module" if can_run else "run_from_module",
        "recommended_from_module": recommended_from_module,
        "messages": messages,
    }


def check_module_produces(
    run_dir: str | Path,
    module_name: str,
    contracts: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Check whether a finished module wrote its declared outputs.

    The check intentionally mirrors input resolution order: manifest
    key_outputs, artifacts.db, then the conventional workspace module path.
    Directory artifacts must contain at least one file so an empty output
    folder cannot satisfy image/audio/video batch contracts.
    """
    contract = get_module_contract(module_name, contracts)
    produces = contract.get("produces", [])
    if not isinstance(produces, list):
        return False, [f"Invalid produces config for {module_name}: expected list"]

    messages: list[str] = []
    ok = True
    for produced in produces:
        if not isinstance(produced, dict):
            ok = False
            messages.append(f"Invalid produce item for {module_name}: {produced!r}")
            continue

        producer_module = produced.get("module") or module_name
        artifact_name = produced.get("name")
        artifact_type = str(produced.get("type") or "file")
        optional = bool(produced.get("optional", False))
        candidates = _candidate_artifact_paths(Path(run_dir), produced, module_name)
        matched = next((path for path in candidates if _artifact_exists_for_type(path, artifact_type)), None)
        label = "optional output" if optional else "required output"

        if matched:
            messages.append(f"Found {label} for {module_name}: {producer_module}.{artifact_name} -> {matched}")
            continue

        checked = ", ".join(str(path) for path in candidates) or "no candidate paths"
        message = (
            f"Missing {label} for {module_name}: "
            f"{producer_module}.{artifact_name} ({artifact_type}); checked: {checked}"
        )
        messages.append(message)
        if not optional:
            ok = False

    return ok, messages


def describe_contract(module_name: str, contracts: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = get_module_contract(module_name, contracts)
    return {
        "requires": contract.get("requires", []),
        "produces": contract.get("produces", []),
    }
