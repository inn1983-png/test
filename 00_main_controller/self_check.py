from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PIPELINE = [
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 00 controller self-check without invoking LLM, ComfyUI, TTS, LTX, or ffmpeg.")
    parser.add_argument("--keep", action="store_true", help="Keep generated self-check workspace directories.")
    return parser


def run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def assert_file(path: Path, label: str) -> None:
    if not path.exists():
        raise AssertionError(f"Missing {label}: {path}")


def assert_dir(path: Path, label: str) -> None:
    if not path.exists() or not path.is_dir():
        raise AssertionError(f"Missing directory {label}: {path}")


def check_pipeline_config() -> None:
    pipeline = read_json(ROOT_DIR / "pipeline.json")
    actual = pipeline.get("pipeline")
    if actual != EXPECTED_PIPELINE:
        raise AssertionError(f"pipeline order mismatch: expected={EXPECTED_PIPELINE}, actual={actual}")


def check_project_context(project_id: str) -> None:
    run_dir = ROOT_DIR / "workspace" / "projects" / project_id
    assert_file(run_dir / "runtime_context.json", "project runtime_context.json")
    assert_file(run_dir / "manifest.json", "project manifest.json")
    assert_file(run_dir / "artifacts.db", "project artifacts.db")
    assert_file(run_dir / "run_status.json", "project run_status.json")

    context = read_json(run_dir / "runtime_context.json")
    if context.get("mode") != "project":
        raise AssertionError("Project self-check context mode is not project")
    if context.get("project_id") != project_id:
        raise AssertionError("Project self-check project_id mismatch")


def check_book_context(book_id: str, chapter_id: str) -> None:
    book_dir = ROOT_DIR / "workspace" / "books" / book_id
    run_dir = book_dir / "chapters" / chapter_id

    assert_file(run_dir / "runtime_context.json", "chapter runtime_context.json")
    assert_file(run_dir / "manifest.json", "chapter manifest.json")
    assert_file(run_dir / "artifacts.db", "chapter artifacts.db")
    assert_file(run_dir / "run_status.json", "chapter run_status.json")

    for relative_path in [
        "shared_assets/characters/characters.json",
        "shared_assets/characters/character_alias_map.json",
        "shared_assets/scenes/scenes.json",
        "shared_assets/scenes/scene_alias_map.json",
        "shared_assets/props/props.json",
        "shared_assets/props/prop_alias_map.json",
        "shared_assets/voice_library/voices.json",
        "global_memory/book_summary.json",
        "global_memory/relationship_map.json",
        "global_memory/timeline_global.json",
        "global_memory/unresolved_clues.json",
        "global_memory/style_bible.md",
    ]:
        assert_file(book_dir / relative_path, f"book bootstrap file {relative_path}")

    context = read_json(run_dir / "runtime_context.json")
    if context.get("mode") != "book_chapter":
        raise AssertionError("Book self-check context mode is not book_chapter")
    if context.get("book_id") != book_id or context.get("chapter_id") != chapter_id:
        raise AssertionError("Book self-check id mismatch")


def check_module_entrypoints() -> None:
    for module_name in EXPECTED_PIPELINE:
        module_dir = ROOT_DIR / module_name
        assert_dir(module_dir, module_name)
        run_staged = module_dir / "run_staged.py"
        run_py = module_dir / "run.py"
        if not run_staged.exists() and not run_py.exists():
            raise AssertionError(f"Missing module entrypoint: {module_name}/run_staged.py or run.py")


def cleanup(project_id: str, book_id: str) -> None:
    for path in [ROOT_DIR / "workspace" / "projects" / project_id, ROOT_DIR / "workspace" / "books" / book_id]:
        if path.exists():
            shutil.rmtree(path)


def main() -> int:
    args = build_parser().parse_args()
    project_id = "self_check_project"
    book_id = "self_check_book"
    chapter_id = "chapter_001"

    if not args.keep:
        cleanup(project_id, book_id)

    commands = [
        [sys.executable, "00_main_controller/validate_pipeline.py", "--pipeline", "pipeline.json", "--strict-order"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--empty-pipeline"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "book_chapter", "--book-id", book_id, "--chapter-id", chapter_id, "--empty-pipeline"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--dry-run", "--strict-order"],
    ]

    for command in commands:
        code, output = run_command(command)
        print("$ " + " ".join(command))
        print(output.rstrip())
        if code != 0:
            print(f"[SELF_CHECK] command failed: {code}")
            return code

    try:
        check_pipeline_config()
        check_project_context(project_id)
        check_book_context(book_id, chapter_id)
        check_module_entrypoints()
    except Exception as exc:  # noqa: BLE001
        print(f"[SELF_CHECK] failed: {exc}")
        return 1
    finally:
        if not args.keep:
            cleanup(project_id, book_id)

    print("[SELF_CHECK] 00 controller self-check passed. No heavy model modules were executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
