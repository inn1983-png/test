from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

io_utils = import_module("00_common.io_utils")
module_runner = import_module("00_common.module_runner")
workspace_manager = import_module("00_common.workspace_manager")
validate_pipeline = import_module("00_main_controller.validate_pipeline")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the modular AI short drama pipeline.")
    parser.add_argument("--mode", choices=["project", "book_chapter"], default="project", help="Run mode.")
    parser.add_argument("--project-id", default=None, help="Short project id. Auto-generated when omitted.")
    parser.add_argument("--book-id", default=None, help="Long novel book id, required for book_chapter mode.")
    parser.add_argument("--chapter-id", default=None, help="Chapter id, required for book_chapter mode.")
    parser.add_argument("--pipeline", default="pipeline.json", help="Pipeline config file path.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip pipeline validation before running.")
    parser.add_argument("--strict-order", action="store_true", help="Warn when modules differ from recommended 01→10 order.")
    parser.add_argument(
        "--empty-pipeline",
        action="store_true",
        help="Only create runtime context and stores, then exit without running modules.",
    )
    return parser


def create_context(args: argparse.Namespace):
    if args.mode == "project":
        return workspace_manager.create_project_context(project_id=args.project_id)

    if not args.book_id or not args.chapter_id:
        raise ValueError("book_chapter mode requires --book-id and --chapter-id")

    return workspace_manager.create_book_chapter_context(book_id=args.book_id, chapter_id=args.chapter_id)


def load_pipeline_config(pipeline_arg: str) -> dict:
    pipeline_path = ROOT_DIR / pipeline_arg
    return io_utils.read_json(pipeline_path, default={})


def main() -> int:
    args = build_parser().parse_args()
    pipeline_config = load_pipeline_config(args.pipeline)

    if not args.empty_pipeline and not args.skip_validation:
        ok, messages = validate_pipeline.validate_pipeline_config(
            pipeline_config,
            strict_order=args.strict_order,
        )
        for message in messages:
            print(message)
        if not ok:
            return 1

    pipeline = [] if args.empty_pipeline else pipeline_config.get("pipeline", [])

    if not args.empty_pipeline and not pipeline:
        print("No pipeline configured. Please edit pipeline.json or use --empty-pipeline for 00 self-check.")
        return 1

    context = create_context(args)
    print("Runtime context:")
    print(workspace_manager.dump_context_for_log(context))

    if args.empty_pipeline:
        print("Empty pipeline finished. Runtime context and artifact stores were initialized.")
        return 0

    for module_name in pipeline:
        code = module_runner.run_module(module_name, context=context)
        if code != 0:
            print(f"Pipeline stopped at: {module_name}")
            return code

    print("Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
