from __future__ import annotations

import json
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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

ALL_MODULES = COMMON_MODULES + CONTROLLER_MODULES + STAGE_MODULES


def run_import_check() -> dict:
    results: list[dict] = []
    passed = 0
    failed = 0

    for mod_name in ALL_MODULES:
        try:
            import_module(mod_name)
            results.append({"module": mod_name, "status": "passed", "error": None})
            passed += 1
        except Exception as exc:
            results.append({"module": mod_name, "status": "failed", "error": str(exc)})
            failed += 1

    status = "failed" if failed else "passed"
    report = {
        "status": status,
        "total": len(ALL_MODULES),
        "passed": passed,
        "failed": failed,
        "results": results,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    output_dir = ROOT / "workspace" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "import_check_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    result = run_import_check()
    sys.exit(1 if result["status"] == "failed" else 0)
