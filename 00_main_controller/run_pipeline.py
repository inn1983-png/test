from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

io_utils = import_module("00_common.io_utils")
module_contracts = import_module("00_common.module_contracts")
module_runner = import_module("00_common.module_runner")
run_status = import_module("00_common.run_status")
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
    parser.add_argument("--skip-dependency-check", action="store_true", help="Skip module input dependency checks.")
    parser.add_argument("--strict-order", action="store_true", help="Warn when modules differ from recommended 01→10 order.")
    parser.add_argument("--from-module", default=None, help="Start running from the specified module in pipeline order.")
    parser.add_argument("--only-module", default=None, help="Run only one specified module.")
    parser.add_argument("--dry-run", action="store_true", help="Print runtime plan without executing modules.")
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


def load_pipeline_config(pipeline_arg: str) -> dict[str, Any]:
    pipeline_path = ROOT_DIR / pipeline_arg
    data = io_utils.read_json(pipeline_path, default={})
    return data if isinstance(data, dict) else {}


def select_pipeline(pipeline: list[str], from_module: str | None = None, only_module: str | None = None) -> tuple[list[str], list[str]]:
    messages: list[str] = []

    if from_module and only_module:
        return [], ["Cannot use --from-module and --only-module together."]

    if only_module:
        if only_module not in pipeline:
            return [], [f"--only-module not found in pipeline: {only_module}"]
        return [only_module], [f"Selected only module: {only_module}"]

    if from_module:
        if from_module not in pipeline:
            return [], [f"--from-module not found in pipeline: {from_module}"]
        index = pipeline.index(from_module)
        selected = pipeline[index:]
        messages.append(f"Selected pipeline from {from_module}: {selected}")
        return selected, messages

    return pipeline, messages


def print_dry_run_plan(context: Any, selected_pipeline: list[str], contracts: dict[str, Any]) -> None:
    print("Dry-run plan:")
    print(f"  mode: {context.mode}")
    print(f"  run_id: {context.run_id}")
    print(f"  run_dir: {context.run_dir}")
    print(f"  input_dir: {context.input_dir}")
    print(f"  shared_assets_dir: {context.shared_assets_dir}")
    print(f"  global_memory_dir: {context.global_memory_dir}")
    print("  modules:")
    for module_name in selected_pipeline:
        contract = module_contracts.describe_contract(module_name, contracts)
        print(f"    - {module_name}")
        print(f"      input_dir: {context.module_input_dir(module_name)}")
        print(f"      output_dir: {context.module_output_dir(module_name)}")
        print(f"      requires: {contract.get('requires', [])}")
        print(f"      produces: {contract.get('produces', [])}")


def check_dependencies_for_module(run_dir: str, module_name: str, contracts: dict[str, Any]) -> bool:
    ok, messages = module_contracts.check_module_requires(run_dir, module_name, contracts)
    for message in messages:
        print(f"[DEPENDENCY] {message}")
    return ok


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

    raw_pipeline = [] if args.empty_pipeline else pipeline_config.get("pipeline", [])
    pipeline = [name for name in raw_pipeline if isinstance(name, str)]

    if not args.empty_pipeline and not pipeline:
        print("No pipeline configured. Please edit pipeline.json or use --empty-pipeline for 00 self-check.")
        return 1

    selected_pipeline, selection_messages = select_pipeline(
        pipeline,
        from_module=args.from_module,
        only_module=args.only_module,
    )
    for message in selection_messages:
        print(message)
    if not args.empty_pipeline and not selected_pipeline:
        return 1

    context = create_context(args)
    print("Runtime context:")
    print(workspace_manager.dump_context_for_log(context))

    if args.empty_pipeline:
        run_status.initialize_status(context.run_dir, [])
        print("Empty pipeline finished. Runtime context and artifact stores were initialized.")
        return 0

    contracts = module_contracts.load_contracts()
    run_status.initialize_status(context.run_dir, selected_pipeline)

    if args.dry_run:
        print_dry_run_plan(context, selected_pipeline, contracts)
        print("Dry-run finished. No modules were executed.")
        return 0

    for module_name in selected_pipeline:
        if not args.skip_dependency_check:
            dependencies_ok = check_dependencies_for_module(context.run_dir, module_name, contracts)
            if not dependencies_ok:
                run_status.mark_module(
                    context.run_dir,
                    module_name,
                    status="blocked",
                    return_code=1,
                    message="missing required upstream artifact",
                )
                print(f"Pipeline blocked before: {module_name}")
                return 1

        code = module_runner.run_module(module_name, context=context)
        if code != 0:
            print(f"Pipeline stopped at: {module_name}")
            return code

    print("Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
