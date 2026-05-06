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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the modular AI short drama pipeline.")
    parser.add_argument("--mode", choices=["project", "book_chapter"], default="project", help="Run mode.")
    parser.add_argument("--project-id", default=None, help="Short project id. Auto-generated when omitted.")
    parser.add_argument("--book-id", default=None, help="Long novel book id, required for book_chapter mode.")
    parser.add_argument("--chapter-id", default=None, help="Chapter id, required for book_chapter mode.")
    parser.add_argument("--pipeline", default="pipeline.json", help="Pipeline config file path.")
    return parser


def create_context(args: argparse.Namespace):
    if args.mode == "project":
        return workspace_manager.create_project_context(project_id=args.project_id)

    if not args.book_id or not args.chapter_id:
        raise ValueError("book_chapter mode requires --book-id and --chapter-id")

    return workspace_manager.create_book_chapter_context(book_id=args.book_id, chapter_id=args.chapter_id)


def main() -> int:
    args = build_parser().parse_args()
    pipeline_path = ROOT_DIR / args.pipeline
    pipeline_config = io_utils.read_json(pipeline_path, default={})
    pipeline = pipeline_config.get("pipeline", [])

    if not pipeline:
        print("No pipeline configured. Please edit pipeline.json.")
        return 1

    context = create_context(args)
    print("Runtime context:")
    print(workspace_manager.dump_context_for_log(context))

    for module_name in pipeline:
        code = module_runner.run_module(module_name, context=context)
        if code != 0:
            print(f"Pipeline stopped at: {module_name}")
            return code

    print("Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
