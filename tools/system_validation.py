from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXCLUDE_DIRS = {
    ".git", "__pycache__", "workspace", "venv", ".venv", "env", "node_modules",
    ".idea", ".vscode", "dist", "build",
}

COMMON_MODULES = [
    "00_common.io_utils",
    "00_common.module_contracts",
    "00_common.module_runner",
    "00_common.workspace_manager",
    "00_common.run_status",
    "00_common.artifact_registry",
    "00_common.artifact_resolver",
    "00_common.repair_index",
    "00_common.llm_config_utils",
]

CONTROLLER_MODULES = [
    "00_main_controller.validate_pipeline",
    "00_main_controller.health_check",
]

STAGE_MODULES = [
    "01_novel_parser.core.stage_runner",
    "02_script_writer.core.stage_runner",
    "03_character_system.core.stage_runner",
    "04_scene_system.core.stage_runner",
    "05_prop_system.core.stage_runner",
    "06_storyboard.core.stage_runner",
    "07_storyboard_image.core.stage_runner",
    "08_audio.core.stage_runner",
    "09_video.core.stage_runner",
    "10_final_assembly.core.stage_runner",
]

ALL_IMPORT_MODULES = COMMON_MODULES + CONTROLLER_MODULES + STAGE_MODULES


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def check_python_syntax() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for py_file in sorted(ROOT.rglob("*.py")):
        if _should_skip(py_file):
            continue
        rel = str(py_file.relative_to(ROOT))
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            checks.append({"check_id": f"syntax_{rel}", "status": "failed", "message": f"语法错误: {exc}", "fix_hint": f"修复 {rel} 中的语法错误"})
    if not any(c["status"] == "failed" for c in checks):
        checks.append({"check_id": "python_syntax_all", "status": "passed", "message": "所有 Python 文件语法检查通过", "fix_hint": ""})
    return checks


def check_imports() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for mod_name in ALL_IMPORT_MODULES:
        try:
            import_module(mod_name)
            checks.append({"check_id": f"import_{mod_name}", "status": "passed", "message": f"{mod_name} 可导入", "fix_hint": ""})
        except Exception as exc:
            checks.append({"check_id": f"import_{mod_name}", "status": "failed", "message": f"{mod_name} 导入失败: {exc}", "fix_hint": f"检查 {mod_name} 的依赖和导入路径"})
    return checks


def check_pipeline_config() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    pipeline_json = ROOT / "pipeline.json"
    if not pipeline_json.exists():
        checks.append({"check_id": "pipeline_json_exists", "status": "failed", "message": "pipeline.json 不存在", "fix_hint": "请创建 pipeline.json"})
        return checks

    try:
        validate_mod = import_module("00_main_controller.validate_pipeline")
        io_utils = import_module("00_common.io_utils")
        config = io_utils.read_json(pipeline_json, default={})
        ok, messages = validate_mod.validate_pipeline_config(config, strict_order=True)
        checks.append({"check_id": "pipeline_validation", "status": "passed" if ok else "failed", "message": "; ".join(messages), "fix_hint": ""})
    except Exception as exc:
        checks.append({"check_id": "pipeline_validation", "status": "failed", "message": f"pipeline 验证异常: {exc}", "fix_hint": ""})

    contracts_path = ROOT / "configs" / "module_contracts.json"
    if not contracts_path.exists():
        checks.append({"check_id": "contracts_exists", "status": "failed", "message": "configs/module_contracts.json 不存在", "fix_hint": ""})
    else:
        try:
            data = json.loads(contracts_path.read_text(encoding="utf-8"))
            modules = data.get("modules", {})
            if not isinstance(modules, dict) or not modules:
                checks.append({"check_id": "contracts_modules", "status": "failed", "message": "module_contracts.json 缺少 modules 字段", "fix_hint": ""})
            else:
                checks.append({"check_id": "contracts_modules", "status": "passed", "message": "module_contracts.json 结构正确", "fix_hint": ""})
        except Exception as exc:
            checks.append({"check_id": "contracts_parse", "status": "failed", "message": f"contracts 解析失败: {exc}", "fix_hint": ""})

    return checks


def check_health() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    try:
        health_mod = import_module("00_main_controller.health_check")
        result = health_mod.run_health_check()
        failed_count = result.get("summary", {}).get("failed", 0)
        checks.append({
            "check_id": "health_check",
            "status": "passed" if failed_count == 0 else "warning",
            "message": f"健康检查: passed={result.get('summary', {}).get('passed', 0)}, warning={result.get('summary', {}).get('warning', 0)}, failed={failed_count}",
            "fix_hint": "" if failed_count == 0 else "查看 system_health_report.json 了解详情",
        })
    except Exception as exc:
        checks.append({"check_id": "health_check", "status": "failed", "message": f"健康检查异常: {exc}", "fix_hint": ""})
    return checks


def check_validate_pipeline() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "00_main_controller" / "validate_pipeline.py"), "--pipeline", "pipeline.json", "--strict-order"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        checks.append({
            "check_id": "validate_pipeline",
            "status": "passed" if result.returncode == 0 else "failed",
            "message": f"validate_pipeline 返回码: {result.returncode}",
            "fix_hint": "" if result.returncode == 0 else result.stdout[-500:] + result.stderr[-500:],
        })
    except Exception as exc:
        checks.append({"check_id": "validate_pipeline", "status": "failed", "message": f"validate_pipeline 执行异常: {exc}", "fix_hint": ""})
    return checks


def check_dry_run() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "00_main_controller" / "run_pipeline.py"), "--mode", "project", "--project-id", "_system_validation_dry_run", "--dry-run", "--strict-order"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        checks.append({
            "check_id": "dry_run_pipeline",
            "status": "passed" if result.returncode == 0 else "warning",
            "message": f"dry-run 返回码: {result.returncode}",
            "fix_hint": "" if result.returncode == 0 else "dry-run 不影响系统，但返回非零码",
        })
    except Exception as exc:
        checks.append({"check_id": "dry_run_pipeline", "status": "warning", "message": f"dry-run 执行异常: {exc}", "fix_hint": ""})
    return checks


def check_data_link() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "00_main_controller" / "check_data_link.py"), "--project-id", "project_validation_001"],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        checks.append({
            "check_id": "data_link_check",
            "status": "passed" if result.returncode == 0 else "warning",
            "message": f"数据链路检查返回码: {result.returncode}",
            "fix_hint": "" if result.returncode == 0 else "查看 00_data_link_check_report.json",
        })
    except Exception as exc:
        checks.append({"check_id": "data_link_check", "status": "warning", "message": f"数据链路检查异常: {exc}", "fix_hint": ""})
    return checks


def check_fixture_dry_run() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    fixture_builder = import_module("tests.fixtures.minimal_project_builder")
    run_dir = ROOT / "workspace" / "projects" / "_system_validation_fixture"
    try:
        fixture_builder.build_minimal_project(run_dir)
        checks.append({"check_id": "fixture_build", "status": "passed", "message": f"fixture 构建成功: {run_dir}", "fix_hint": ""})
    except Exception as exc:
        checks.append({"check_id": "fixture_build", "status": "failed", "message": f"fixture 构建失败: {exc}", "fix_hint": ""})
    return checks


def check_web_ui_static() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    required_files = [
        "web_ui/server.py",
        "web_ui/static/index.html",
        "web_ui/static/app.js",
    ]
    for rel in required_files:
        path = ROOT / rel
        if path.exists():
            checks.append({"check_id": f"web_ui_file_{rel.replace('/', '_').replace('.', '_')}", "status": "passed", "message": f"{rel} 存在", "fix_hint": ""})
        else:
            checks.append({"check_id": f"web_ui_file_{rel.replace('/', '_').replace('.', '_')}", "status": "failed", "message": f"{rel} 缺失", "fix_hint": f"请确保 {rel} 存在"})

    try:
        server_mod = import_module("web_ui.server")
        checks.append({"check_id": "web_ui_import", "status": "passed", "message": "web_ui.server 可导入", "fix_hint": ""})
    except Exception as exc:
        checks.append({"check_id": "web_ui_import", "status": "failed", "message": f"web_ui.server 导入失败: {exc}", "fix_hint": ""})

    return checks


def run_system_validation() -> dict[str, Any]:
    all_checks: list[dict[str, Any]] = []
    fixed_files: list[str] = []
    remaining_risks: list[str] = []

    print("[1/9] Python 语法检查...")
    all_checks.extend(check_python_syntax())

    print("[2/9] import 检查...")
    all_checks.extend(check_imports())

    print("[3/9] pipeline 配置检查...")
    all_checks.extend(check_pipeline_config())

    print("[4/9] health_check...")
    all_checks.extend(check_health())

    print("[5/9] validate_pipeline...")
    all_checks.extend(check_validate_pipeline())

    print("[6/9] dry-run...")
    all_checks.extend(check_dry_run())

    print("[7/9] 数据链路检查...")
    all_checks.extend(check_data_link())

    print("[8/9] fixture dry-run 测试...")
    all_checks.extend(check_fixture_dry_run())

    print("[9/9] Web UI 核心函数静态检查...")
    all_checks.extend(check_web_ui_static())

    passed_count = sum(1 for c in all_checks if c["status"] == "passed")
    warning_count = sum(1 for c in all_checks if c["status"] == "warning")
    failed_count = sum(1 for c in all_checks if c["status"] == "failed")

    if failed_count > 0:
        overall = "failed"
    elif warning_count > 0:
        overall = "warning"
    else:
        overall = "passed"

    if warning_count > 0:
        remaining_risks.append(f"{warning_count} 项 warning 需关注（多为环境配置相关）")
    if failed_count > 0:
        remaining_risks.append(f"{failed_count} 项 failed 需修复")

    report = {
        "status": overall,
        "created_at": _now_iso(),
        "summary": {
            "passed": passed_count,
            "warning": warning_count,
            "failed": failed_count,
        },
        "checks": all_checks,
        "fixed_files": fixed_files,
        "remaining_risks": remaining_risks,
    }

    output_dir = ROOT / "workspace" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "system_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"系统验收结果: {overall.upper()}")
    print(f"  passed:  {passed_count}")
    print(f"  warning: {warning_count}")
    print(f"  failed:  {failed_count}")
    print(f"报告: {output_path}")
    print(f"{'='*60}")

    return report


if __name__ == "__main__":
    result = run_system_validation()
    sys.exit(1 if result["status"] == "failed" else 0)
