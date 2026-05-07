from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
EXPECTED_MODULES = [
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
EXPECTED_DISPLAY_PIPELINE = ["00_main_controller", *EXPECTED_MODULES]

MODULE_DATA_LINK: dict[str, dict[str, Any]] = {
    "01_novel_parser": {
        "expected_inputs": [],
        "expected_outputs": ["01_novel_parser/novel_analysis.json"],
    },
    "02_script_writer": {
        "expected_inputs": ["01_novel_parser/novel_analysis.json"],
        "expected_outputs": ["02_script_writer/script.json"],
    },
    "03_character_system": {
        "expected_inputs": ["01_novel_parser/novel_analysis.json", "02_script_writer/script.json"],
        "expected_outputs": ["03_character_system/characters.json"],
    },
    "04_scene_system": {
        "expected_inputs": ["01_novel_parser/novel_analysis.json", "02_script_writer/script.json"],
        "expected_outputs": ["04_scene_system/scenes.json"],
    },
    "05_prop_system": {
        "expected_inputs": ["01_novel_parser/novel_analysis.json", "02_script_writer/script.json"],
        "expected_outputs": ["05_prop_system/props.json"],
    },
    "06_storyboard": {
        "expected_inputs": ["02_script_writer/script.json", "03_character_system/characters.json", "04_scene_system/scenes.json", "05_prop_system/props.json"],
        "expected_outputs": ["06_storyboard/storyboard.json"],
    },
    "07_storyboard_image": {
        "expected_inputs": ["06_storyboard/storyboard.json"],
        "expected_outputs": ["07_storyboard_image/image_manifest.json"],
    },
    "08_audio": {
        "expected_inputs": ["02_script_writer/script.json"],
        "expected_outputs": ["08_audio/final_audio.wav", "08_audio/audio_timeline.json", "08_audio/subtitle.srt", "08_audio/subtitle.ass"],
    },
    "09_video": {
        "expected_inputs": ["07_storyboard_image/image_manifest.json", "08_audio/final_audio.wav", "08_audio/audio_timeline.json"],
        "expected_outputs": ["09_video/video_manifest.json"],
    },
    "10_final_assembly": {
        "expected_inputs": ["09_video/video_manifest.json", "08_audio/final_audio.wav"],
        "expected_outputs": ["10_final_assembly/final_manifest.json", "10_final_assembly/final_meta.json"],
    },
}

CORE_FILES_BY_MODULE: dict[str, list[str]] = {
    "01_novel_parser": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "02_script_writer": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "03_character_system": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "04_scene_system": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "05_prop_system": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "06_storyboard": ["run_staged.py", "core/stage_runner.py", "core/llm_client.py", "core/json_repair.py", "core/quality_checker.py", "core/schema_validator.py"],
    "07_storyboard_image": ["run_staged.py", "core/stage_runner.py", "core/comfyui_client.py", "core/quality_checker.py", "core/schema_validator.py"],
    "08_audio": ["run_staged.py", "core/stage_runner.py", "core/indextts_client.py", "core/voice_library.py", "core/timeline_builder.py", "core/quality_checker.py", "core/schema_validator.py"],
    "09_video": ["run_staged.py", "core/stage_runner.py", "core/workflow_adapter.py", "core/comfyui_client.py", "core/quality_checker.py", "core/schema_validator.py"],
    "10_final_assembly": ["run_staged.py", "core/stage_runner.py", "core/ffmpeg_client.py", "core/quality_checker.py", "core/schema_validator.py"],
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def add_result(results: list[dict[str, Any]], status: str, item: str, message: str, path: str | None = None) -> None:
    results.append({"status": status, "item": item, "message": message, "path": path})
    mark = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}.get(status, "[INFO]")
    suffix = f" ({path})" if path else ""
    print(f"{mark} {item}: {message}{suffix}")


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


def check_pipeline(results: list[dict[str, Any]]) -> None:
    pipeline_path = ROOT_DIR / "pipeline.json"
    if not pipeline_path.exists():
        add_result(results, "fail", "pipeline.json", "pipeline.json 不存在", "pipeline.json")
        return
    data = read_json(pipeline_path)
    pipeline = data.get("pipeline", []) if isinstance(data, dict) else []
    if pipeline == EXPECTED_MODULES:
        add_result(results, "pass", "pipeline order", "01–10 顺序正确", "pipeline.json")
    else:
        add_result(results, "fail", "pipeline order", f"应为 {EXPECTED_MODULES}，实际为 {pipeline}", "pipeline.json")


def check_contracts(results: list[dict[str, Any]]) -> None:
    path = ROOT_DIR / "configs" / "module_contracts.json"
    if not path.exists():
        add_result(results, "fail", "module contracts", "configs/module_contracts.json 不存在", str(path.relative_to(ROOT_DIR)))
        return
    data = read_json(path)
    modules = data.get("modules", {}) if isinstance(data, dict) else {}
    for module in EXPECTED_MODULES:
        contract = modules.get(module)
        if not isinstance(contract, dict):
            add_result(results, "fail", f"contract {module}", "缺少模块契约", "configs/module_contracts.json")
            continue
        produces = contract.get("produces", [])
        add_result(results, "pass", f"contract {module}", f"requires={len(contract.get('requires', []))}, produces={len(produces)}", "configs/module_contracts.json")

    checks = [
        ("08_audio", "final_audio.wav"),
        ("08_audio", "audio_timeline.json"),
        ("09_video", "video_manifest.json"),
        ("10_final_assembly", "final.mp4"),
        ("10_final_assembly", "final_manifest.json"),
        ("10_final_assembly", "final_meta.json"),
    ]
    for module, name in checks:
        produces = modules.get(module, {}).get("produces", []) if isinstance(modules.get(module), dict) else []
        if any(item.get("name") == name for item in produces if isinstance(item, dict)):
            add_result(results, "pass", f"contract output {module}/{name}", "关键产物已登记", "configs/module_contracts.json")
        else:
            add_result(results, "fail", f"contract output {module}/{name}", "关键产物未登记", "configs/module_contracts.json")


def check_files(results: list[dict[str, Any]]) -> None:
    root_files = [
        "00_main_controller/run_pipeline.py",
        "00_main_controller/validate_pipeline.py",
        "00_main_controller/self_check.py",
        "00_main_controller/check_data_link.py",
        "00_common/module_runner.py",
        "00_common/module_contracts.py",
        "00_common/workspace_manager.py",
        "web_ui/server.py",
        "web_ui/static/index.html",
        "web_ui/static/app.js",
    ]
    for rel in root_files:
        status = "pass" if (ROOT_DIR / rel).exists() else "fail"
        add_result(results, status, rel, "存在" if status == "pass" else "缺失", rel)

    for module, files in CORE_FILES_BY_MODULE.items():
        if not (ROOT_DIR / module).is_dir():
            add_result(results, "fail", module, "模块目录缺失", module)
            continue
        add_result(results, "pass", module, "模块目录存在", module)
        for rel_file in files:
            rel = f"{module}/{rel_file}"
            if (ROOT_DIR / rel).exists():
                add_result(results, "pass", rel, "存在", rel)
            else:
                add_result(results, "fail", rel, "缺失", rel)


def check_project_data_link(results: list[dict[str, Any]], project_id: str) -> None:
    run_dir = ROOT_DIR / "workspace" / "projects" / project_id
    if not run_dir.exists():
        add_result(results, "warn", "project_data_link", f"项目目录不存在: {project_id}")
        return

    def _module_has_run(mod: str) -> bool:
        status_file = run_dir / mod / "status.json"
        if status_file.exists():
            return True
        for suffix in ("_analysis.json", ".json"):
            candidate = run_dir / mod / f"{mod}{suffix}"
            if candidate.exists():
                return True
        return False

    for module_name, link_info in MODULE_DATA_LINK.items():
        expected_inputs = link_info.get("expected_inputs", [])
        expected_outputs = link_info.get("expected_outputs", [])

        found_inputs: list[str] = []
        missing_inputs: list[str] = []
        for inp in expected_inputs:
            if (run_dir / inp).exists():
                found_inputs.append(inp)
            else:
                missing_inputs.append(inp)

        found_outputs: list[str] = []
        missing_outputs: list[str] = []
        for out in expected_outputs:
            if (run_dir / out).exists():
                found_outputs.append(out)
            else:
                missing_outputs.append(out)

        if missing_inputs or missing_outputs:
            upstream_ran = all(
                _module_has_run(inp.split("/")[0]) for inp in missing_inputs
            ) if missing_inputs else True
            if missing_inputs and upstream_ran:
                status = "fail"
            elif missing_inputs:
                status = "warn"
            elif missing_outputs and _module_has_run(module_name):
                status = "fail"
            else:
                status = "warn"
            parts = []
            if missing_inputs:
                parts.append(f"缺失输入: {missing_inputs}")
            if missing_outputs:
                parts.append(f"缺失输出: {missing_outputs}")
            add_result(results, status, f"data_link_{module_name}", "; ".join(parts))
        else:
            add_result(results, "pass", f"data_link_{module_name}", f"输入{len(found_inputs)}项, 输出{len(found_outputs)}项均存在")


def check_controller_commands(results: list[dict[str, Any]], project_id: str) -> None:
    commands = [
        [sys.executable, "00_main_controller/validate_pipeline.py", "--pipeline", "pipeline.json", "--strict-order"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--empty-pipeline"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "book_chapter", "--book-id", f"{project_id}_book", "--chapter-id", "chapter_001", "--empty-pipeline"],
        [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--dry-run", "--strict-order"],
    ]
    for command in commands:
        code, output = run_command(command)
        printable = " ".join(command)
        if code == 0:
            add_result(results, "pass", printable, "命令通过")
        else:
            add_result(results, "fail", printable, f"返回码 {code}\n{output[-1200:]}")


def write_report(project_id: str, results: list[dict[str, Any]]) -> Path:
    failed = [item for item in results if item["status"] == "fail"]
    warnings = [item for item in results if item["status"] == "warn"]
    report = {
        "checked_at": now_iso(),
        "project_id": project_id,
        "display_pipeline": EXPECTED_DISPLAY_PIPELINE,
        "execution_pipeline": EXPECTED_MODULES,
        "summary": {
            "total": len(results),
            "passed": sum(1 for item in results if item["status"] == "pass"),
            "warnings": len(warnings),
            "failed": len(failed),
            "passed_all": not failed,
        },
        "results": results,
    }
    run_dir = ROOT_DIR / "workspace" / "projects" / project_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "00_data_link_check_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[REPORT] {report_path.relative_to(ROOT_DIR)}")
    return report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check 00-10 controller/UI/module data link without running LLM, ComfyUI, TTS, LTX, or ffmpeg.")
    parser.add_argument("--project-id", default="ui_data_link_check", help="Workspace project id used for check reports.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results: list[dict[str, Any]] = []
    print("[CHECK] 00-10 data link and code skeleton check started.")
    check_pipeline(results)
    check_contracts(results)
    check_files(results)
    check_project_data_link(results, args.project_id)
    check_controller_commands(results, args.project_id)
    report_path = write_report(args.project_id, results)
    failed = [item for item in results if item["status"] == "fail"]
    if failed:
        print(f"[CHECK] failed: {len(failed)} issue(s). See {report_path.relative_to(ROOT_DIR)}")
        return 1
    print("[CHECK] passed: 00-10 data link is structurally connected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
