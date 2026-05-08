from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from importlib import import_module
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

io_utils = import_module("00_common.io_utils")
style_context = import_module("00_common.style_context")
module_contracts = import_module("00_common.module_contracts")

REQUIRED_STYLE_FILES = [
    "style_bible.json",
    "style_bible.md",
    "style_prompt_prefix.txt",
    "image_style_lock.txt",
    "video_style_lock.txt",
    "style_negative_prompt.txt",
    "style_meta.json",
]

TEXT_LLM_MODULES = [
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
]

IMAGE_MODULE = "07_storyboard_image"
VIDEO_MODULE = "09_video"
STYLE_MODULE = "00_style_system"


def _bool_status(ok: bool) -> str:
    return "passed" if ok else "failed"


def _file_check(run_dir: Path, filename: str) -> dict[str, Any]:
    path = run_dir / STYLE_MODULE / filename
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    return {
        "file": filename,
        "path": str(path),
        "exists": exists,
        "size": size,
        "status": _bool_status(exists and size > 0),
    }


def _contract_check() -> list[dict[str, Any]]:
    contracts = module_contracts.load_contracts()
    rows: list[dict[str, Any]] = []
    for module_name in [*TEXT_LLM_MODULES, IMAGE_MODULE, VIDEO_MODULE, "10_final_assembly"]:
        contract = module_contracts.get_module_contract(module_name, contracts)
        requires = contract.get("requires", []) if isinstance(contract, dict) else []
        required_names = {
            str(item.get("name"))
            for item in requires
            if isinstance(item, dict) and item.get("module") == STYLE_MODULE
        }
        if module_name in TEXT_LLM_MODULES:
            expected = {"style_bible.json"}
            if module_name != "01_novel_parser":
                expected.add("style_prompt_prefix.txt")
        elif module_name == IMAGE_MODULE:
            expected = {"style_bible.json", "image_style_lock.txt", "style_negative_prompt.txt"}
        elif module_name == VIDEO_MODULE:
            expected = {"style_bible.json", "video_style_lock.txt"}
        else:
            expected = {"style_bible.json"}
        missing = sorted(expected - required_names)
        rows.append({
            "module": module_name,
            "expected_style_requires": sorted(expected),
            "actual_style_requires": sorted(required_names),
            "missing": missing,
            "status": _bool_status(not missing),
        })
    return rows


def _runtime_read_check(run_dir: Path) -> dict[str, Any]:
    os.environ["AI_DRAMA_RUN_DIR"] = str(run_dir)
    bible = style_context.load_style_bible(run_dir)
    prompt_prefix = style_context.load_style_prompt_prefix(run_dir)
    image_lock = style_context.load_image_style_lock(run_dir)
    video_lock = style_context.load_video_style_lock(run_dir)
    negative = style_context.load_style_negative_prompt(run_dir)
    return {
        "style_id": bible.get("style_id") if isinstance(bible, dict) else None,
        "display_name": bible.get("display_name") if isinstance(bible, dict) else None,
        "style_bible_loaded": bool(bible),
        "prompt_prefix_loaded": bool(prompt_prefix.strip()),
        "image_style_lock_loaded": bool(image_lock.strip()),
        "video_style_lock_loaded": bool(video_lock.strip()),
        "style_negative_prompt_loaded": bool(negative.strip()),
        "status": _bool_status(bool(bible) and bool(prompt_prefix.strip()) and bool(image_lock.strip()) and bool(video_lock.strip()) and bool(negative.strip())),
    }


def _source_static_check() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    source_expectations = [
        (ROOT_DIR / "00_common" / "llm_prompt_guard.py", ["style_context", "load_style_prompt_prefix", "build_style_summary_for_llm"]),
        (ROOT_DIR / "07_storyboard_image" / "core" / "prompt_builder.py", ["load_image_style_lock", "load_style_negative_prompt"]),
        (ROOT_DIR / "00_main_controller" / "sitecustomize.py", ["load_video_style_lock", "load_style_negative_prompt", "09_video.core.workflow_adapter"]),
        (ROOT_DIR / "web_ui" / "static" / "style_picker.js", ["style_preset", "getSelectedStylePreset"]),
    ]
    for path, needles in source_expectations:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [needle for needle in needles if needle not in text]
        checks.append({
            "path": str(path.relative_to(ROOT_DIR)),
            "expected_markers": needles,
            "missing_markers": missing,
            "status": _bool_status(path.exists() and not missing),
        })
    return checks


def check_style_chain(run_dir: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir or Path(os.getenv("AI_DRAMA_RUN_DIR", ""))
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "check": "style_chain",
        "run_dir": str(run_dir) if run_dir else "",
        "style_files": [],
        "runtime_read_check": {},
        "contract_check": _contract_check(),
        "source_static_check": _source_static_check(),
        "issues": [],
    }

    if run_dir and run_dir.exists():
        result["style_files"] = [_file_check(run_dir, filename) for filename in REQUIRED_STYLE_FILES]
        result["runtime_read_check"] = _runtime_read_check(run_dir)
    else:
        result["issues"].append({"issue": "run_dir_missing", "message": "Run dir not provided or does not exist; runtime file checks skipped."})

    for section_name in ["style_files", "contract_check", "source_static_check"]:
        for row in result.get(section_name, []) or []:
            if row.get("status") != "passed":
                result["issues"].append({"issue": section_name, "detail": row})
    if result.get("runtime_read_check") and result["runtime_read_check"].get("status") != "passed":
        result["issues"].append({"issue": "runtime_read_check", "detail": result["runtime_read_check"]})

    result["status"] = "passed" if not result["issues"] else "failed"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check whether STYLE_BIBLE is wired through 00→09.")
    parser.add_argument("--run-dir", default=os.getenv("AI_DRAMA_RUN_DIR", ""), help="Workspace run dir, for example workspace/projects/project_test")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    result = check_style_chain(run_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        io_utils.write_json(args.output, result)
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
