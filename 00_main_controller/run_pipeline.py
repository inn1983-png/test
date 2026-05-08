from __future__ import annotations

import argparse
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

io_utils = import_module("00_common.io_utils")
module_contracts = import_module("00_common.module_contracts")
module_runner = import_module("00_common.module_runner")
resource_manager = import_module("00_common.resource_manager")
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
    parser.add_argument("--to-module", default=None, help="Stop running after the specified module in pipeline order.")
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


def select_pipeline(
    pipeline: list[str],
    from_module: str | None = None,
    only_module: str | None = None,
    to_module: str | None = None,
) -> tuple[list[str], list[str]]:
    messages: list[str] = []

    if not pipeline:
        return [], []

    if only_module and (from_module or to_module):
        return [], ["Cannot use --only-module together with --from-module or --to-module."]

    if only_module:
        if only_module not in pipeline:
            return [], [f"--only-module not found in pipeline: {only_module}"]
        return [only_module], [f"Selected only module: {only_module}"]

    start_index = 0
    end_index = len(pipeline) - 1

    if from_module:
        if from_module not in pipeline:
            return [], [f"--from-module not found in pipeline: {from_module}"]
        start_index = pipeline.index(from_module)

    if to_module:
        if to_module not in pipeline:
            return [], [f"--to-module not found in pipeline: {to_module}"]
        end_index = pipeline.index(to_module)

    if start_index > end_index:
        return [], [f"Invalid module range: {from_module or pipeline[start_index]} is after {to_module or pipeline[end_index]}"]

    selected = pipeline[start_index : end_index + 1]
    if from_module or to_module:
        messages.append(f"Selected pipeline range: {selected}")
    return selected, messages


def print_dry_run_plan(context: Any, selected_pipeline: list[str], contracts: dict[str, Any]) -> None:
    print("Dry-run plan:")
    print(f"  mode: {context.mode}")
    print(f"  run_id: {context.run_id}")
    print(f"  run_dir: {context.run_dir}")
    print(f"  input_dir: {context.input_dir}")
    print(f"  shared_assets_dir: {context.shared_assets_dir}")
    print(f"  global_memory_dir: {context.global_memory_dir}")
    print(f"  style_preset: {os.getenv('AI_DRAMA_STYLE_PRESET', '')}")
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


def _save_config_snapshot(context: Any, args: argparse.Namespace, selected_pipeline: list[str], pipeline_config: dict[str, Any]) -> None:
    api_key = os.getenv("AI_DRAMA_LLM_API_KEY", "")
    snapshot = {
        "snapshot_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "style": {
            "selected_preset": os.getenv("AI_DRAMA_STYLE_PRESET", ""),
            "note": "Only the selected style preset id is passed into the run. Full preset lists are not sent to downstream LLM stages.",
        },
        "llm": {
            "base_url": os.getenv("AI_DRAMA_LLM_BASE_URL", ""),
            "model": os.getenv("AI_DRAMA_LLM_MODEL", ""),
            "temperature": os.getenv("AI_DRAMA_LLM_TEMPERATURE", ""),
            "timeout_sec": os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", ""),
            "has_api_key": bool(api_key),
        },
        "image": {
            "execution_mode": os.getenv("AI_DRAMA_IMAGE_EXECUTION_MODE", "dry_run"),
            "comfyui_base_url": os.getenv("AI_DRAMA_COMFYUI_BASE_URL", ""),
            "workflow": os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", ""),
            "workflow_mapping": os.getenv("AI_DRAMA_COMFYUI_WORKFLOW_MAPPING", ""),
        },
        "audio": {
            "execution_mode": os.getenv("AI_DRAMA_AUDIO_EXECUTION_MODE", "dry_run"),
            "index_tts_root": os.getenv("AI_DRAMA_INDEX_TTS_ROOT", "index-tts"),
            "voice_map": os.getenv("AI_DRAMA_VOICE_MAP", ""),
        },
        "video": {
            "execution_mode": os.getenv("AI_DRAMA_VIDEO_EXECUTION_MODE", "dry_run"),
            "workflow": os.getenv("AI_DRAMA_VIDEO_WORKFLOW", ""),
            "workflow_mapping": os.getenv("AI_DRAMA_VIDEO_WORKFLOW_MAPPING", ""),
            "ffmpeg": os.getenv("AI_DRAMA_FFMPEG", "ffmpeg"),
        },
        "resource_release": {
            "device": os.getenv("DEVICE", "cuda"),
            "auto_release_gpu": os.getenv("AUTO_RELEASE_GPU", "true"),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        },
        "run_args": {
            "mode": args.mode,
            "project_id": args.project_id,
            "book_id": args.book_id,
            "chapter_id": args.chapter_id,
            "pipeline_file": args.pipeline,
            "from_module": args.from_module,
            "to_module": args.to_module,
            "only_module": args.only_module,
            "dry_run": args.dry_run,
        },
        "selected_pipeline": selected_pipeline,
        "runtime_context": {
            "mode": context.mode,
            "run_id": context.run_id,
            "run_dir": str(context.run_dir),
            "input_dir": str(context.input_dir),
        },
    }
    snapshot_path = Path(context.run_dir) / "config_snapshot.json"
    io_utils.write_json(snapshot_path, snapshot)
    print(f"[SNAPSHOT] config_snapshot.json saved to {snapshot_path}")


def handle_phase_transition(previous_module: str | None, next_module: str) -> None:
    """Release model families only at explicit pipeline phase boundaries."""
    if previous_module == "06_storyboard" and next_module == "07_storyboard_image":
        resource_manager.release_llm_resources()
    if previous_module == "07_storyboard_image" and next_module == "08_audio":
        resource_manager.release_image_resources()
    if previous_module == "08_audio" and next_module == "09_video":
        resource_manager.release_audio_resources()
    if previous_module == "08_audio" and next_module == "09_video":
        # LTX2.3 should start with other large model families unloaded.
        resource_manager.release_image_resources()
    if previous_module == "09_video" and next_module == "10_final_assembly":
        resource_manager.release_video_resources()


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
        to_module=args.to_module,
    )
    for message in selection_messages:
        print(message)
    if not args.empty_pipeline and not selected_pipeline:
        return 1

    context = create_context(args)
    os.environ["AI_DRAMA_RUN_DIR"] = str(context.run_dir)
    print("Runtime context:")
    print(workspace_manager.dump_context_for_log(context))
    print(f"[STYLE] selected preset: {os.getenv('AI_DRAMA_STYLE_PRESET', '') or 'default'}")

    _save_config_snapshot(context, args, selected_pipeline, pipeline_config)

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

    previous_module: str | None = None
    for module_name in selected_pipeline:
        handle_phase_transition(previous_module, module_name)

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
        previous_module = module_name

    print("Pipeline finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
