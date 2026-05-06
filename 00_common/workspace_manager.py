from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from importlib import import_module

io_utils = import_module("00_common.io_utils")

ROOT_DIR = Path(__file__).resolve().parents[1]

RunMode = Literal["project", "book_chapter"]


@dataclass
class RuntimeContext:
    """Runtime paths shared by all modules in one pipeline run.

    Code lives in module folders. Runtime data lives under workspace/.
    """

    mode: RunMode
    run_id: str
    project_id: str | None
    book_id: str | None
    chapter_id: str | None
    root_dir: str
    workspace_dir: str
    run_dir: str
    input_dir: str
    shared_assets_dir: str | None
    global_memory_dir: str | None

    def module_dir(self, module_name: str) -> Path:
        return Path(self.run_dir) / module_name

    def module_input_dir(self, module_name: str) -> Path:
        return self.module_dir(module_name) / "input"

    def module_output_dir(self, module_name: str) -> Path:
        return self.module_dir(module_name)


def make_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def create_project_context(project_id: str | None = None) -> RuntimeContext:
    project_id = project_id or make_run_id("project")
    run_dir = ROOT_DIR / "workspace" / "projects" / project_id
    input_dir = run_dir / "input"

    io_utils.ensure_dir(input_dir)

    context = RuntimeContext(
        mode="project",
        run_id=project_id,
        project_id=project_id,
        book_id=None,
        chapter_id=None,
        root_dir=str(ROOT_DIR),
        workspace_dir=str(ROOT_DIR / "workspace"),
        run_dir=str(run_dir),
        input_dir=str(input_dir),
        shared_assets_dir=None,
        global_memory_dir=None,
    )
    save_context(context)
    return context


def create_book_chapter_context(book_id: str, chapter_id: str) -> RuntimeContext:
    book_dir = ROOT_DIR / "workspace" / "books" / book_id
    run_dir = book_dir / "chapters" / chapter_id
    input_dir = run_dir / "input"
    shared_assets_dir = book_dir / "shared_assets"
    global_memory_dir = book_dir / "global_memory"

    for path in [
        input_dir,
        shared_assets_dir / "characters" / "images",
        shared_assets_dir / "scenes" / "images",
        shared_assets_dir / "props" / "images",
        shared_assets_dir / "voice_library" / "samples",
        global_memory_dir,
    ]:
        io_utils.ensure_dir(path)

    context = RuntimeContext(
        mode="book_chapter",
        run_id=f"{book_id}_{chapter_id}",
        project_id=None,
        book_id=book_id,
        chapter_id=chapter_id,
        root_dir=str(ROOT_DIR),
        workspace_dir=str(ROOT_DIR / "workspace"),
        run_dir=str(run_dir),
        input_dir=str(input_dir),
        shared_assets_dir=str(shared_assets_dir),
        global_memory_dir=str(global_memory_dir),
    )
    save_context(context)
    bootstrap_shared_asset_files(context)
    return context


def save_context(context: RuntimeContext) -> None:
    context_path = Path(context.run_dir) / "runtime_context.json"
    io_utils.write_json(context_path, asdict(context))


def load_context(path: str | Path) -> RuntimeContext:
    data = io_utils.read_json(path, default={})
    return RuntimeContext(**data)


def context_to_env(context: RuntimeContext, module_name: str) -> dict[str, str]:
    module_output_dir = context.module_output_dir(module_name)
    module_input_dir = context.module_input_dir(module_name)
    io_utils.ensure_dir(module_input_dir)
    io_utils.ensure_dir(module_output_dir)

    context_path = Path(context.run_dir) / "runtime_context.json"

    env = {
        "AI_DRAMA_MODE": context.mode,
        "AI_DRAMA_RUN_ID": context.run_id,
        "AI_DRAMA_RUN_DIR": context.run_dir,
        "AI_DRAMA_INPUT_DIR": context.input_dir,
        "AI_DRAMA_MODULE_NAME": module_name,
        "AI_DRAMA_MODULE_INPUT_DIR": str(module_input_dir),
        "AI_DRAMA_MODULE_OUTPUT_DIR": str(module_output_dir),
        "AI_DRAMA_CONTEXT_PATH": str(context_path),
    }

    if context.project_id:
        env["AI_DRAMA_PROJECT_ID"] = context.project_id
    if context.book_id:
        env["AI_DRAMA_BOOK_ID"] = context.book_id
    if context.chapter_id:
        env["AI_DRAMA_CHAPTER_ID"] = context.chapter_id
    if context.shared_assets_dir:
        env["AI_DRAMA_SHARED_ASSETS_DIR"] = context.shared_assets_dir
    if context.global_memory_dir:
        env["AI_DRAMA_GLOBAL_MEMORY_DIR"] = context.global_memory_dir

    return env


def bootstrap_shared_asset_files(context: RuntimeContext) -> None:
    if not context.shared_assets_dir:
        return

    base = Path(context.shared_assets_dir)
    defaults = {
        base / "characters" / "characters.json": [],
        base / "characters" / "character_alias_map.json": {},
        base / "scenes" / "scenes.json": [],
        base / "scenes" / "scene_alias_map.json": {},
        base / "props" / "props.json": [],
        base / "props" / "prop_alias_map.json": {},
        base / "voice_library" / "voices.json": [],
    }

    for path, value in defaults.items():
        if not path.exists():
            io_utils.write_json(path, value)

    global_memory = Path(context.global_memory_dir or "")
    if global_memory:
        memory_defaults = {
            global_memory / "book_summary.json": {},
            global_memory / "relationship_map.json": {},
            global_memory / "timeline_global.json": [],
            global_memory / "unresolved_clues.json": [],
        }
        for path, value in memory_defaults.items():
            if not path.exists():
                io_utils.write_json(path, value)
        style_bible = global_memory / "style_bible.md"
        if not style_bible.exists():
            style_bible.write_text("# Style Bible\n\n", encoding="utf-8")


def dump_context_for_log(context: RuntimeContext) -> str:
    return json.dumps(asdict(context), ensure_ascii=False, indent=2)
