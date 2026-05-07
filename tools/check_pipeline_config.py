from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from importlib import import_module

io_utils = import_module("00_common.io_utils")
validate_pipeline_mod = import_module("00_main_controller.validate_pipeline")

EXPECTED_ORDER = [
    "01_novel_parser", "02_script_writer", "03_character_system",
    "04_scene_system", "05_prop_system", "06_storyboard",
    "07_storyboard_image", "08_audio", "09_video", "10_final_assembly",
]


def run_pipeline_validation() -> dict:
    checks: list[dict] = []

    pipeline_json = ROOT / "pipeline.json"
    if not pipeline_json.exists():
        checks.append({"check_id": "pipeline_json_exists", "status": "failed", "message": "pipeline.json 不存在", "fix_hint": "请创建 pipeline.json"})
    else:
        config = io_utils.read_json(pipeline_json, default={})
        ok, messages = validate_pipeline_mod.validate_pipeline_config(config, strict_order=True)
        checks.append({"check_id": "pipeline_validation", "status": "passed" if ok else "failed", "message": "; ".join(messages), "fix_hint": ""})

        pipeline_list = config.get("pipeline", [])
        for module_name in EXPECTED_ORDER:
            if module_name not in pipeline_list:
                checks.append({"check_id": f"pipeline_module_{module_name}", "status": "failed", "message": f"{module_name} 不在 pipeline 列表中", "fix_hint": f"请将 {module_name} 添加到 pipeline.json"})
            else:
                module_dir = ROOT / module_name
                run_staged = module_dir / "run_staged.py"
                if not module_dir.exists():
                    checks.append({"check_id": f"module_dir_{module_name}", "status": "failed", "message": f"{module_name} 目录不存在", "fix_hint": ""})
                elif not run_staged.exists():
                    checks.append({"check_id": f"module_entry_{module_name}", "status": "failed", "message": f"{module_name}/run_staged.py 不存在", "fix_hint": ""})
                else:
                    checks.append({"check_id": f"module_{module_name}", "status": "passed", "message": f"{module_name} 目录和入口文件存在", "fix_hint": ""})

    contracts_path = ROOT / "configs" / "module_contracts.json"
    if not contracts_path.exists():
        checks.append({"check_id": "contracts_exists", "status": "failed", "message": "configs/module_contracts.json 不存在", "fix_hint": ""})
    else:
        data = io_utils.read_json(contracts_path, default={})
        modules = data.get("modules", {})
        if not isinstance(modules, dict) or not modules:
            checks.append({"check_id": "contracts_modules", "status": "failed", "message": "module_contracts.json 缺少 modules 字段", "fix_hint": ""})
        else:
            checks.append({"check_id": "contracts_modules", "status": "passed", "message": "module_contracts.json 有 modules 字段", "fix_hint": ""})
            for module_name in EXPECTED_ORDER:
                contract = modules.get(module_name)
                if not isinstance(contract, dict):
                    checks.append({"check_id": f"contract_{module_name}", "status": "failed", "message": f"{module_name} 无 contract", "fix_hint": ""})
                else:
                    has_requires = "requires" in contract
                    has_produces = "produces" in contract
                    if not has_requires or not has_produces:
                        checks.append({"check_id": f"contract_{module_name}", "status": "warning", "message": f"{module_name}: requires={'有' if has_requires else '无'}, produces={'有' if has_produces else '无'}", "fix_hint": f"建议为 {module_name} 添加 requires 和 produces"})
                    else:
                        checks.append({"check_id": f"contract_{module_name}", "status": "passed", "message": f"{module_name}: requires/produces 完整", "fix_hint": ""})

    local_resource_path = ROOT / "configs" / "local_resource_release.json"
    if not local_resource_path.exists():
        checks.append({"check_id": "local_resource_exists", "status": "warning", "message": "configs/local_resource_release.json 不存在", "fix_hint": ""})
    else:
        checks.append({"check_id": "local_resource_exists", "status": "passed", "message": "configs/local_resource_release.json 存在", "fix_hint": ""})

    passed_count = sum(1 for c in checks if c["status"] == "passed")
    failed_count = sum(1 for c in checks if c["status"] == "failed")
    warning_count = sum(1 for c in checks if c["status"] == "warning")

    overall = "failed" if failed_count else ("warning" if warning_count else "passed")
    report = {
        "status": overall,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {"passed": passed_count, "failed": failed_count, "warning": warning_count},
        "checks": checks,
    }

    output_dir = ROOT / "workspace" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pipeline_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    result = run_pipeline_validation()
    sys.exit(1 if result["status"] == "failed" else 0)
