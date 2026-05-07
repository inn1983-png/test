from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PIPELINE_ORDER = [
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

MINIMAL_NOVEL = """第一章 测试

这是一个测试小说，用于验证流水线 dry-run 闭环。

李明站在窗前，看着远方的山峦。
"今天天气真好。"他轻声说道。
王芳走过来，微笑着说："是啊，适合出去走走。"

两人走出房间，沿着小路前行。
远处的山峰在夕阳下显得格外美丽。

（完）
"""


class SmokeTestResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[dict[str, str]] = []
        self.warnings: list[str] = []
        self.start_time = datetime.now()

    def add_pass(self, name: str) -> None:
        self.passed.append(name)

    def add_fail(self, name: str, reason: str) -> None:
        self.failed.append({"name": name, "reason": reason})

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def summary(self) -> str:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        lines = [
            f"Smoke Test Results ({elapsed:.1f}s)",
            f"=" * 50,
            f"PASSED: {len(self.passed)}",
            f"FAILED: {len(self.failed)}",
            f"WARNINGS: {len(self.warnings)}",
            "",
        ]
        if self.passed:
            lines.append("Passed checks:")
            for name in self.passed:
                lines.append(f"  ✓ {name}")
            lines.append("")
        if self.failed:
            lines.append("Failed checks:")
            for item in self.failed:
                lines.append(f"  ✗ {item['name']}: {item['reason']}")
            lines.append("")
        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
            lines.append("")
        overall = "PASSED" if not self.failed else "FAILED"
        lines.append(f"Overall: {overall}")
        return "\n".join(lines)


def test_pipeline_json(result: SmokeTestResult) -> None:
    path = ROOT / "00_main_controller" / "pipeline.json"
    if not path.exists():
        result.add_warning("pipeline.json not found (optional)")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            result.add_fail("pipeline.json format", "must be a JSON object")
            return
        result.add_pass("pipeline.json exists and readable")
    except Exception as exc:
        result.add_fail("pipeline.json parse", str(exc))


def test_module_contracts(result: SmokeTestResult) -> None:
    path = ROOT / "configs" / "module_contracts.json"
    if not path.exists():
        result.add_warning("module_contracts.json not found (optional)")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            result.add_fail("module_contracts.json format", "must be a JSON object")
            return
        for module_name in PIPELINE_ORDER:
            if module_name not in data:
                result.add_warning(f"module_contracts.json missing {module_name}")
        result.add_pass("module_contracts.json exists and readable")
    except Exception as exc:
        result.add_fail("module_contracts.json parse", str(exc))


def test_module_run_staged(result: SmokeTestResult) -> None:
    for module_name in PIPELINE_ORDER:
        module_dir = ROOT / module_name
        run_staged = module_dir / "run_staged.py"
        if not module_dir.exists():
            result.add_fail(f"{module_name}/ exists", f"directory not found: {module_dir}")
            continue
        if not run_staged.exists():
            result.add_fail(f"{module_name}/run_staged.py exists", f"file not found: {run_staged}")
            continue
        result.add_pass(f"{module_name}/run_staged.py exists")


def test_00_common_imports(result: SmokeTestResult) -> None:
    modules_to_test = [
        ("00_common.io_utils", "io_utils"),
        ("00_common.stage_cache", "stage_cache"),
        ("00_common.repair_index", "repair_index"),
        ("00_common.llm_config_utils", "llm_config_utils"),
        ("00_common.llm_truncation_handler", "llm_truncation_handler"),
    ]
    for module_path, name in modules_to_test:
        try:
            __import__(module_path)
            result.add_pass(f"import {module_path}")
        except Exception as exc:
            result.add_fail(f"import {module_path}", str(exc))


def test_health_check(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        health_check = import_module("00_main_controller.health_check")
        report = health_check.run_health_check()
        status = report.get("status")
        if status == "failed":
            failed_checks = [c for c in report.get("checks", []) if c.get("status") == "failed"]
            result.add_fail("health_check", f"status=failed, {len(failed_checks)} checks failed")
        else:
            result.add_pass(f"health_check status={status}")
    except Exception as exc:
        result.add_fail("health_check", str(exc))


def test_schema_validators(result: SmokeTestResult) -> None:
    validators = [
        ("10_final_assembly.core.schema_validator", "validate_final_output"),
    ]
    for module_path, func_name in validators:
        try:
            mod = __import__(module_path, fromlist=[func_name])
            validator_fn = getattr(mod, func_name)
            test_data = {
                "module": "10_final_assembly",
                "schema_version": "1.1",
                "stage_mode": "final_assembly",
                "uses_llm": False,
                "uses_ltx": False,
                "generates_new_video_segments": False,
                "final_video_ready": False,
                "final_video_path": None,
                "final_video_placeholder_path": None,
                "final_manifest_path": "/tmp/final_manifest.json",
                "final_meta_path": "/tmp/final_meta.json",
                "video_manifest_path": None,
                "final_audio_path": None,
                "source": {"video_source_mode": "dry_run_placeholder", "audio_source": "08_audio/final_audio.wav"},
                "subtitle_policy": {"default_burn_subtitles": False, "burn_subtitles": False},
                "stage_status": [
                    {"stage_id": "10A"},
                    {"stage_id": "10B"},
                    {"stage_id": "10C"},
                    {"stage_id": "10D"},
                ],
            }
            result_val = validator_fn(test_data)
            if isinstance(result_val, dict) and "passed" in result_val:
                result.add_pass(f"{module_path}.{func_name} callable")
            else:
                result.add_fail(f"{module_path}.{func_name}", "unexpected return format")
        except Exception as exc:
            result.add_fail(f"{module_path}.{func_name}", str(exc))


def test_truncation_handler(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        handler = import_module("00_common.llm_truncation_handler")
        assert handler.is_truncated({"choices": [{"finish_reason": "length"}]}) is True
        assert handler.is_truncated({"choices": [{"finish_reason": "stop"}]}) is False
        result.add_pass("llm_truncation_handler.is_truncated")
    except Exception as exc:
        result.add_fail("llm_truncation_handler", str(exc))


def test_repair_index(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        repair = import_module("00_common.repair_index")
        tmpdir = ROOT / "workspace" / "projects" / "_smoke_test_tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            result_val = repair.build_repair_index(str(tmpdir))
            if isinstance(result_val, dict) and "issues" in result_val:
                result.add_pass("repair_index.build_repair_index")
            else:
                result.add_fail("repair_index.build_repair_index", "unexpected return format")
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
    except Exception as exc:
        result.add_fail("repair_index", str(exc))


def test_09pre_stage(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        stage_runner = import_module("09_video.core.stage_runner")
        has_09pre = any(s["stage_id"] == "09PRE" for s in stage_runner.STAGES)
        if has_09pre:
            result.add_pass("09_video 09PRE stage exists")
        else:
            result.add_fail("09_video 09PRE stage", "09PRE not found in STAGES")
    except Exception as exc:
        result.add_fail("09_video 09PRE stage", str(exc))


def test_10_no_fake_mp4(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        schema = import_module("10_final_assembly.core.schema_validator")
        test_data = {
            "module": "10_final_assembly",
            "schema_version": "1.1",
            "stage_mode": "final_assembly",
            "uses_llm": False,
            "uses_ltx": False,
            "generates_new_video_segments": False,
            "final_video_ready": False,
            "final_video_path": None,
            "final_video_placeholder_path": None,
            "final_manifest_path": "/tmp/final_manifest.json",
            "final_meta_path": "/tmp/final_meta.json",
            "video_manifest_path": None,
            "final_audio_path": None,
            "source": {"video_source_mode": "dry_run_placeholder", "audio_source": "08_audio/final_audio.wav"},
            "subtitle_policy": {"default_burn_subtitles": False, "burn_subtitles": False},
            "stage_status": [
                {"stage_id": "10A"},
                {"stage_id": "10B"},
                {"stage_id": "10C"},
                {"stage_id": "10D"},
            ],
        }
        result_val = schema.validate_final_output(test_data)
        if result_val.get("passed"):
            result.add_pass("10 schema_validator accepts dry_run_placeholder")
        else:
            result.add_fail("10 schema_validator dry_run_placeholder", str(result_val.get("issues")))
    except Exception as exc:
        result.add_fail("10 schema_validator", str(exc))


def test_reference_pollution_check(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        stage_runner = import_module("07_storyboard_image.core.stage_runner")
        assert hasattr(stage_runner, "_validate_reference_sources")
        result.add_pass("07 _validate_reference_sources exists")
    except Exception as exc:
        result.add_fail("07 _validate_reference_sources", str(exc))


def test_text_length_review(result: SmokeTestResult) -> None:
    try:
        from importlib import import_module
        stage_runner = import_module("08_audio.core.stage_runner")
        assert hasattr(stage_runner, "build_text_length_review")
        review = stage_runner.build_text_length_review([
            {"text": "短文本", "line_type": "D"},
            {"text": "这是一段很长的文本，用来测试文本长度预警功能是否正常工作，当文本超过一定字符数时应该触发预警" * 3, "line_type": "D"},
        ])
        if isinstance(review, dict) and "long_texts" in review:
            result.add_pass("08 build_text_length_review")
        else:
            result.add_fail("08 build_text_length_review", "unexpected return format")
    except Exception as exc:
        result.add_fail("08 build_text_length_review", str(exc))


def run_all_tests() -> SmokeTestResult:
    result = SmokeTestResult()
    print("Running smoke tests...")
    print()

    tests = [
        ("Pipeline JSON", test_pipeline_json),
        ("Module Contracts", test_module_contracts),
        ("Module run_staged.py", test_module_run_staged),
        ("00_common imports", test_00_common_imports),
        ("Health Check", test_health_check),
        ("Schema Validators", test_schema_validators),
        ("Truncation Handler", test_truncation_handler),
        ("Repair Index", test_repair_index),
        ("09PRE Stage", test_09pre_stage),
        ("10 No Fake MP4", test_10_no_fake_mp4),
        ("07 Reference Pollution", test_reference_pollution_check),
        ("08 Text Length Review", test_text_length_review),
    ]

    for name, test_fn in tests:
        print(f"  Testing: {name}...", end=" ")
        try:
            test_fn(result)
            print("done")
        except Exception as exc:
            result.add_fail(name, f"unexpected error: {exc}")
            print(f"ERROR: {exc}")

    return result


if __name__ == "__main__":
    result = run_all_tests()
    print()
    print(result.summary())
    sys.exit(0 if not result.failed else 1)
