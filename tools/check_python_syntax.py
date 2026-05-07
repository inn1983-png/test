from __future__ import annotations

import json
import py_compile
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git", "__pycache__", "workspace", "venv", ".venv", "env", "node_modules",
    ".idea", ".vscode", "dist", "build",
}


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def run_syntax_check() -> dict:
    checked_files = 0
    failed_files: list[dict] = []

    for py_file in sorted(ROOT.rglob("*.py")):
        if should_skip(py_file):
            continue
        rel = str(py_file.relative_to(ROOT))
        checked_files += 1
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            failed_files.append({"path": rel, "error": str(exc)})

    status = "failed" if failed_files else "passed"
    report = {
        "status": status,
        "checked_files": checked_files,
        "failed_files": failed_files,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    output_dir = ROOT / "workspace" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "python_syntax_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    result = run_syntax_check()
    sys.exit(1 if result["status"] == "failed" else 0)
