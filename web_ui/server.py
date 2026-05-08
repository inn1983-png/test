from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
PIPELINE_FILE = ROOT_DIR / "pipeline.json"
WORKSPACE_DIR = ROOT_DIR / "workspace"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

module_contracts = import_module("00_common.module_contracts")
repair_index = import_module("00_common.repair_index")
event_writer = import_module("00_common.event_writer")

TEXT_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
}

DISPLAY_PIPELINE_PREFIX = "00_main_controller"
MOJIBAKE_MARKERS = ("�", "½", "¼", "¾", "Ã", "Â", "ä", "å", "è", "é")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def repair_mojibake_text(text: str) -> str:
    """Best-effort repair for Chinese text that was decoded with the wrong code page.

    On Windows, subprocess output can pass through cp936/gbk/cp1252 before the Web UI
    reads it. This function is intentionally conservative: it only replaces the text
    when a candidate clearly contains more CJK characters and fewer replacement marks.
    """
    if not text or not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text

    def cjk_score(value: str) -> int:
        return sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")

    def bad_score(value: str) -> int:
        return value.count("�") * 3 + sum(value.count(ch) for ch in ("½", "¼", "¾", "Ã", "Â"))

    candidates = [text]
    transforms = [
        ("latin1", "utf-8"),
        ("latin1", "gbk"),
        ("cp1252", "utf-8"),
        ("cp1252", "gbk"),
        ("gbk", "utf-8"),
    ]
    for source, target in transforms:
        try:
            candidates.append(text.encode(source, errors="ignore").decode(target, errors="ignore"))
        except Exception:
            pass
    best = max(candidates, key=lambda item: (cjk_score(item) - bad_score(item), cjk_score(item), -bad_score(item), len(item)))
    if cjk_score(best) > cjk_score(text) and bad_score(best) <= bad_score(text):
        return best
    return text


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return json.loads(repair_mojibake_text(path.read_text(encoding=encoding)))
        except Exception:
            pass
    return default


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def safe_id(raw: str | None, prefix: str = "project") -> str:
    raw = (raw or "").strip()
    if not raw:
        return prefix + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    value = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in raw).strip("_")
    return value or prefix + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_rel_path(raw: str) -> Path:
    raw = unquote(raw).replace("\\", "/")
    parts = [part for part in raw.split("/") if part and part not in {".", ".."}]
    return Path(*parts) if parts else Path()


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def resolve_run_dir(raw: str | None) -> Path | None:
    value = unquote(str(raw or "").strip())
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / safe_rel_path(value)
    candidate = candidate.resolve()
    workspace = WORKSPACE_DIR.resolve()
    if candidate == workspace or workspace in candidate.parents:
        return candidate
    return None


@dataclass
class Job:
    id: str
    mode: str
    project_id: str | None
    book_id: str | None
    chapter_id: str | None
    command: list[str]
    run_dir: Path
    kind: str = "pipeline"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    status: str = "queued"
    return_code: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    subscribers: list[queue.Queue[dict[str, Any]]] = field(default_factory=list)
    process: subprocess.Popen[str] | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"time": now_iso(), "type": event_type, "payload": payload}
        with self.lock:
            self.updated_at = event["time"]
            self.events.append(event)
            self.events = self.events[-2000:]
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except Exception:
                pass


class JobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def add(self, job: Job) -> None:
        with self.lock:
            self.jobs[job.id] = job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def list(self) -> list[Job]:
        with self.lock:
            return sorted(self.jobs.values(), key=lambda item: item.created_at, reverse=True)


JOBS = JobStore()


def load_pipeline() -> dict[str, Any]:
    data = read_json(PIPELINE_FILE, {"pipeline": []})
    pipeline = data.get("pipeline", []) if isinstance(data, dict) else []
    if isinstance(pipeline, list):
        data["display_pipeline"] = [DISPLAY_PIPELINE_PREFIX, *pipeline]
    return data


def project_run_dir(project_id: str) -> Path:
    return WORKSPACE_DIR / "projects" / project_id


def book_chapter_run_dir(book_id: str, chapter_id: str) -> Path:
    return WORKSPACE_DIR / "books" / book_id / "chapters" / chapter_id


def summarize_run_status(status: dict[str, Any]) -> str:
    modules = status.get("modules", {}) if isinstance(status, dict) else {}
    if not modules:
        return "not_started"
    values = [str((item or {}).get("status", "pending")) for item in modules.values() if isinstance(item, dict)]
    if any(value == "running" for value in values):
        return "running"
    if any(value == "failed" for value in values):
        return "failed"
    if any(value == "blocked" for value in values):
        return "blocked"
    if values and all(value in {"success", "skipped"} for value in values):
        return "success"
    return "pending"


def discover_projects() -> list[dict[str, Any]]:
    base = WORKSPACE_DIR / "projects"
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(base.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not item.is_dir():
            continue
        status = read_json(item / "run_status.json", {})
        link_report = read_json(item / "00_data_link_check_report.json", {})
        archived = (item / "project_archived.json").exists()
        rows.append({
            "project_id": item.name,
            "run_dir": rel_path(item),
            "updated_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat(timespec="seconds"),
            "status": "archived" if archived else summarize_run_status(status),
            "archived": archived,
            "data_link_check": link_report.get("summary", {}) if isinstance(link_report, dict) else {},
        })
    return rows[:100]


def file_row(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": rel_path(path),
        "size": path.stat().st_size if path.exists() else 0,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,
    }


def discover_module_outputs(module_dir: Path) -> list[dict[str, Any]]:
    if not module_dir.exists():
        return []
    rows = [file_row(path) for path in sorted(module_dir.glob("*.json"))]
    for subdir in ["images", "segments", "clips"]:
        folder = module_dir / subdir
        if folder.exists():
            rows.extend(file_row(path) for path in sorted(folder.glob("*"))[:60] if path.is_file())
    return rows


def discover_stage_outputs(module_dir: Path) -> list[dict[str, Any]]:
    inter = module_dir / "intermediate"
    if not inter.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(inter.glob("*.json")):
        row = file_row(path)
        data = read_json(path, {})
        if isinstance(data, dict):
            quality = data.get("stage_quality") or data.get("quality_report") or {}
            row["stage_id"] = data.get("stage") or data.get("stage_id") or path.name.split("_")[0]
            row["score"] = quality.get("score") if isinstance(quality, dict) else None
            row["passed"] = quality.get("passed") if isinstance(quality, dict) else None
            row["issues_count"] = len(quality.get("issues", [])) if isinstance(quality, dict) and isinstance(quality.get("issues"), list) else 0
            stage_prefix = str(path.name.split("_")[0])
            trace_root = module_dir / "llm_traces"
            if trace_root.exists():
                trace_dirs = sorted(trace_root.glob(f"{stage_prefix}*_attempt_*"))
                request_path = next((trace_dir / "request.json" for trace_dir in trace_dirs if (trace_dir / "request.json").exists()), None)
                if request_path:
                    row["llm_trace_request_path"] = rel_path(request_path)
                    row["llm_trace_dir"] = rel_path(request_path.parent)
        rows.append(row)
    return rows


def discover_quality(module_dir: Path) -> dict[str, Any]:
    for path in sorted(module_dir.glob("*.json")):
        data = read_json(path, {})
        if isinstance(data, dict):
            if isinstance(data.get("quality_report"), dict):
                return data["quality_report"]
            if isinstance(data.get("stage_quality"), dict):
                return data["stage_quality"]
    return {}


def discover_important_outputs(run_dir: Path) -> list[dict[str, Any]]:
    names = [
        "00_data_link_check_report.json",
        "runtime_context.json",
        "manifest.json",
        "run_status.json",
        "01_novel_parser/novel_analysis.json",
        "02_script_writer/script.json",
        "03_character_system/characters.json",
        "04_scene_system/scenes.json",
        "05_prop_system/props.json",
        "06_storyboard/storyboard.json",
        "06_storyboard/storyboard_meta.json",
        "07_storyboard_image/image_manifest.json",
        "08_audio/final_audio.wav",
        "08_audio/audio_timeline.json",
        "08_audio/subtitle.srt",
        "08_audio/subtitle.ass",
        "09_video/video_manifest.json",
        "09_video/final_video.mp4",
        "10_final_assembly/final.mp4",
        "10_final_assembly/final.placeholder.txt",
        "10_final_assembly/final_manifest.json",
        "10_final_assembly/final_meta.json",
    ]
    return [file_row(run_dir / name) for name in names if (run_dir / name).exists()]


def discover_run_snapshot(run_dir: Path) -> dict[str, Any]:
    pipeline = load_pipeline().get("pipeline", [])
    status = read_json(run_dir / "run_status.json", {})
    modules = [{
        "name": "00_main_controller",
        "status": "success" if (run_dir / "runtime_context.json").exists() or (run_dir / "00_data_link_check_report.json").exists() else "pending",
        "message": "运行上下文 / 数据链路检查",
        "exists": (ROOT_DIR / "00_main_controller").exists(),
        "outputs": [file_row(path) for path in [run_dir / "runtime_context.json", run_dir / "manifest.json", run_dir / "run_status.json", run_dir / "00_data_link_check_report.json"] if path.exists()],
        "stages": [],
        "quality": read_json(run_dir / "00_data_link_check_report.json", {}).get("summary", {}),
    }]
    for module_name in pipeline:
        module_dir = run_dir / module_name
        module_status = (status.get("modules", {}) or {}).get(module_name, {}) if isinstance(status, dict) else {}
        modules.append({
            "name": module_name,
            "status": module_status.get("status", "pending") if isinstance(module_status, dict) else "pending",
            "message": module_status.get("message", "") if isinstance(module_status, dict) else "",
            "start_time": module_status.get("start_time") if isinstance(module_status, dict) else None,
            "end_time": module_status.get("end_time") if isinstance(module_status, dict) else None,
            "duration_seconds": module_status.get("duration_seconds") if isinstance(module_status, dict) else None,
            "return_code": module_status.get("return_code") if isinstance(module_status, dict) else None,
            "exists": module_dir.exists(),
            "outputs": discover_module_outputs(module_dir),
            "stages": discover_stage_outputs(module_dir),
            "current_stage": read_json(module_dir / "current_stage_status.json", {}),
            "quality": discover_quality(module_dir),
        })
    repair = {}
    try:
        repair = repair_index.write_repair_index(run_dir)
    except Exception as exc:
        repair = {"error": str(exc), "issues": []}
    final_assembly_dir = run_dir / "10_final_assembly"
    final_video_ready = None
    final_video_placeholder_path = None
    final_manifest_data = read_json(final_assembly_dir / "final_manifest.json", {})
    if isinstance(final_manifest_data, dict):
        final_video_ready = final_manifest_data.get("final_video_ready")
        final_video_placeholder_path = final_manifest_data.get("final_video_placeholder_path")
    return {
        "run_dir": rel_path(run_dir),
        "run_status": status,
        "summary_status": summarize_run_status(status),
        "modules": modules,
        "important_outputs": discover_important_outputs(run_dir),
        "data_link_check": read_json(run_dir / "00_data_link_check_report.json", {}),
        "repair_index": repair,
        "events": event_writer.read_recent_events(run_dir, limit=200),
        "final_video_ready": final_video_ready,
        "final_video_placeholder_path": final_video_placeholder_path,
    }


def inspect_module_requirements(query: str) -> tuple[dict[str, Any], int]:
    params = parse_qs(query)
    run_dir = resolve_run_dir((params.get("run_dir") or [""])[0])
    module_name = str((params.get("module") or [""])[0] or "").strip()
    if not run_dir:
        return {"error": "invalid run_dir"}, 400
    if not module_name:
        return {"error": "module is required"}, 400

    contracts = module_contracts.load_contracts()
    data = module_contracts.inspect_module_requirements(run_dir, module_name, contracts)
    data["run_dir"] = rel_path(run_dir)
    return data, 200


def project_repair_index(project_id: str) -> tuple[dict[str, Any], int]:
    raw_project_id = unquote(str(project_id or "")).strip()
    if not raw_project_id:
        return {"error": "project_id is required"}, 400
    safe_project_id = safe_id(raw_project_id, "project")
    run_dir = project_run_dir(safe_project_id)
    if not run_dir.exists():
        return {"error": "project not found"}, 404
    try:
        return repair_index.write_repair_index(run_dir), 200
    except Exception as exc:
        return {"error": str(exc)}, 500


def project_snapshot(project_id: str) -> tuple[dict[str, Any], int]:
    raw_project_id = unquote(str(project_id or "")).strip()
    if not raw_project_id:
        return {"error": "project_id is required"}, 400
    run_dir = project_run_dir(safe_id(raw_project_id, "project"))
    if not run_dir.exists():
        return {"error": "project not found"}, 404
    return {"snapshot": discover_run_snapshot(run_dir)}, 200


def archive_project(project_id: str) -> tuple[dict[str, Any], int]:
    raw_project_id = unquote(str(project_id or "")).strip()
    if not raw_project_id:
        return {"error": "project_id is required"}, 400
    run_dir = project_run_dir(safe_id(raw_project_id, "project"))
    if not run_dir.exists():
        return {"error": "project not found"}, 404
    marker = {
        "project_id": run_dir.name,
        "archived": True,
        "archived_at": now_iso(),
        "mode": "marker_only",
    }
    (run_dir / "project_archived.json").write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"project_id": run_dir.name, "archived": True}, 200


def check_workflow_mapping(query: str) -> tuple[dict[str, Any], int]:
    params = parse_qs(query)
    raw_path = str((params.get("path") or [""])[0] or "").strip()
    path = Path(unquote(raw_path)) if raw_path else ROOT_DIR / "configs" / "comfyui_workflows" / "07_storyboard_image_mapping.json"
    if not path.is_absolute():
        path = ROOT_DIR / safe_rel_path(str(path))
    if not path.exists():
        return {"exists": False, "path": str(path), "workflow_path": "", "missing_nodes": ["mapping file not found"]}, 200
    data = read_json(path, {})
    if not isinstance(data, dict):
        return {"exists": True, "path": str(path), "workflow_path": "", "missing_nodes": ["mapping root must be object"]}, 200

    missing: list[str] = []
    workflow_path = ""
    if "workflow_path" in data:
        workflow_path = str(data.get("workflow_path") or "")
        for key in ("positive_node_id", "negative_node_id", "output_prefix_node_id"):
            if not str(data.get(key) or "").strip():
                missing.append(key)
        refs = data.get("reference_image_nodes", [])
        if isinstance(refs, list):
            for index, item in enumerate(refs):
                if isinstance(item, dict) and not str(item.get("node_id") or "").strip():
                    missing.append(f"reference_image_nodes[{index}].node_id")
    else:
        for route_name, route in data.items():
            if not isinstance(route, dict):
                continue
            workflow_path = workflow_path or str(route.get("workflow_path") or "")
            for key in ("workflow_path", "positive_node_id", "negative_node_id", "output_prefix_node_id"):
                if not str(route.get(key) or "").strip():
                    missing.append(f"{route_name}.{key}")
    return {"exists": True, "path": str(path), "workflow_path": workflow_path, "missing_nodes": missing, "mapping": data}, 200


def build_command(payload: dict[str, Any], run_dir: Path) -> tuple[list[str], dict[str, str], str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONLEGACYWINDOWSSTDIO", "0")
    env.setdefault("CHCP", "65001")
    job_kind = str(payload.get("job_kind") or "pipeline")

    if job_kind == "data_link_check":
        project_id = safe_id(payload.get("project_id"), "ui_data_link_check")
        return [sys.executable, str(ROOT_DIR / "00_main_controller" / "check_data_link.py"), "--project-id", project_id], env, job_kind
    if job_kind == "controller_self_check":
        cmd = [sys.executable, str(ROOT_DIR / "00_main_controller" / "self_check.py")]
        if payload.get("keep_self_check"):
            cmd.append("--keep")
        return cmd, env, job_kind

    mode = payload.get("mode") or "project"
    cmd = [sys.executable, "-X", "utf8", str(ROOT_DIR / "00_main_controller" / "run_pipeline.py"), "--mode", mode]
    if mode == "book_chapter":
        cmd.extend(["--book-id", safe_id(payload.get("book_id"), "book"), "--chapter-id", safe_id(payload.get("chapter_id"), "chapter")])
    else:
        cmd.extend(["--project-id", safe_id(payload.get("project_id"), "project")])

    for key, flag in [("from_module", "--from-module"), ("only_module", "--only-module"), ("to_module", "--to-module")]:
        value = str(payload.get(key) or "").strip()
        if value:
            cmd.extend([flag, value])
    for key, flag in [("skip_validation", "--skip-validation"), ("skip_dependency_check", "--skip-dependency-check"), ("dry_run", "--dry-run"), ("empty_pipeline", "--empty-pipeline")]:
        if payload.get(key):
            cmd.append(flag)
    if payload.get("strict_order", True):
        cmd.append("--strict-order")

    for source_key, env_key in [
        ("llm_api_key", "AI_DRAMA_LLM_API_KEY"),
        ("llm_base_url", "AI_DRAMA_LLM_BASE_URL"),
        ("llm_model", "AI_DRAMA_LLM_MODEL"),
        ("llm_max_tokens", "AI_DRAMA_LLM_MAX_TOKENS"),
        ("llm_input_compact", "AI_DRAMA_LLM_INPUT_COMPACT"),
        ("llm_temperature", "AI_DRAMA_LLM_TEMPERATURE"),
        ("llm_timeout_sec", "AI_DRAMA_LLM_TIMEOUT_SEC"),
        ("image_execution_mode", "AI_DRAMA_IMAGE_EXECUTION_MODE"),
        ("retry_scope", "AI_DRAMA_IMAGE_RETRY_SCOPE"),
        ("image_retry_scope", "AI_DRAMA_IMAGE_RETRY_SCOPE"),
        ("frame_id", "AI_DRAMA_IMAGE_RETRY_FRAME_ID"),
        ("asset_key", "AI_DRAMA_IMAGE_RETRY_ASSET_KEY"),
        ("comfyui_base_url", "AI_DRAMA_COMFYUI_BASE_URL"),
        ("comfyui_workflow", "AI_DRAMA_COMFYUI_WORKFLOW"),
        ("comfyui_workflow_mapping", "AI_DRAMA_COMFYUI_WORKFLOW_MAPPING"),
        ("image_style_suffix", "AI_DRAMA_IMAGE_STYLE_SUFFIX"),
        ("image_negative_prompt", "AI_DRAMA_IMAGE_NEGATIVE_PROMPT"),
        ("audio_execution_mode", "AI_DRAMA_AUDIO_EXECUTION_MODE"),
        ("index_tts_root", "AI_DRAMA_INDEX_TTS_ROOT"),
        ("video_execution_mode", "AI_DRAMA_VIDEO_EXECUTION_MODE"),
        ("ffmpeg_bin", "AI_DRAMA_FFMPEG"),
    ]:
        value = str(payload.get(source_key) or "").strip()
        if value:
            env[env_key] = value
    if payload.get("force") or payload.get("image_retry_force"):
        env["AI_DRAMA_IMAGE_RETRY_FORCE"] = "1"

    style_preset = str(payload.get("style_preset") or "").strip()
    if style_preset:
        env["AI_DRAMA_STYLE_PRESET"] = style_preset
        env["AI_DRAMA_SELECTED_STYLE_PRESET"] = style_preset

    for env_key, default in [
        ("AI_DRAMA_LLM_TIMEOUT_SEC", "6000"),
        ("AI_DRAMA_IMAGE_COMFYUI_TIMEOUT_SEC", "7200"),
        ("AI_DRAMA_VIDEO_COMFYUI_TIMEOUT_SEC", "14400"),
        ("AI_DRAMA_COMFYUI_POLL_INTERVAL_SEC", "5"),
        ("AI_DRAMA_VIDEO_DRY_RUN_PLACEHOLDER_BYTES", "2048"),
    ]:
        if not str(env.get(env_key) or "").strip():
            env[env_key] = default

    return cmd, env, job_kind


def start_job(payload: dict[str, Any]) -> Job:
    mode = payload.get("mode") or "project"
    if mode == "book_chapter":
        book_id = safe_id(payload.get("book_id"), "book")
        chapter_id = safe_id(payload.get("chapter_id"), "chapter")
        run_dir = book_chapter_run_dir(book_id, chapter_id)
        project_id = None
    else:
        project_id = safe_id(payload.get("project_id"), "project")
        book_id = None
        chapter_id = None
        run_dir = project_run_dir(project_id)

    novel_text = str(payload.get("novel_text") or "").strip()
    if novel_text:
        write_text(run_dir / "input" / "novel.txt", novel_text)

    cmd, env, kind = build_command(payload, run_dir)
    job = Job(id=uuid.uuid4().hex[:12], mode=mode, project_id=project_id, book_id=book_id, chapter_id=chapter_id, command=cmd, run_dir=run_dir, kind=kind)
    JOBS.add(job)
    threading.Thread(target=run_job_thread, args=(job, env), daemon=True).start()
    return job


def run_job_thread(job: Job, env: dict[str, str]) -> None:
    job.status = "running"
    job.publish("job_started", {"command": job.command, "run_dir": rel_path(job.run_dir), "kind": job.kind})
    try:
        process = subprocess.Popen(job.command, cwd=str(ROOT_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
        job.process = process
        assert process.stdout is not None
        last_snapshot = 0.0
        for line in process.stdout:
            raw = line.rstrip("\n")
            clean = repair_mojibake_text(raw)
            if clean:
                job.publish("log", {"line": clean})
            if time.time() - last_snapshot > 1.5:
                job.publish("snapshot", discover_run_snapshot(job.run_dir))
                last_snapshot = time.time()
        return_code = process.wait()
        job.return_code = return_code
        job.status = "success" if return_code == 0 else "failed"
        job.publish("snapshot", discover_run_snapshot(job.run_dir))
        job.publish("job_finished", {"return_code": return_code, "status": job.status})
    except Exception as exc:
        job.status = "failed"
        job.return_code = 1
        job.publish("job_error", {"error": str(exc)})


def job_summary(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "mode": job.mode,
        "project_id": job.project_id,
        "book_id": job.book_id,
        "chapter_id": job.chapter_id,
        "run_dir": rel_path(job.run_dir),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "status": job.status,
        "return_code": job.return_code,
        "command": job.command,
    }


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/pipeline":
            return self.send_json(load_pipeline())
        if path == "/api/projects":
            return self.send_json({"projects": discover_projects()})
        if path == "/api/module-requirements":
            data, status = inspect_module_requirements(parsed.query)
            return self.send_json(data, status=status)
        if path == "/api/comfyui-workflow-mapping/check":
            data, status = check_workflow_mapping(parsed.query)
            return self.send_json(data, status=status)
        if path == "/api/jobs":
            return self.send_json({"jobs": [job_summary(job) for job in JOBS.list()]})
        if path == "/api/system/snapshot":
            return self.send_json({"pipeline": load_pipeline(), "projects": discover_projects()})
        if path.startswith("/api/jobs/") and path.endswith("/events"):
            return self.stream_events(path.split("/")[3])
        if path.startswith("/api/jobs/") and path.endswith("/snapshot"):
            job = JOBS.get(path.split("/")[3])
            if not job:
                return self.send_json({"error": "job not found"}, status=404)
            return self.send_json({"job": job_summary(job), "snapshot": discover_run_snapshot(job.run_dir)})
        if path.startswith("/api/projects/") and path.endswith("/repair-index"):
            parts = path.split("/")
            project_id = parts[3] if len(parts) > 3 else ""
            data, status = project_repair_index(project_id)
            return self.send_json(data, status=status)
        if path.startswith("/api/projects/") and path.endswith("/snapshot"):
            parts = path.split("/")
            project_id = parts[3] if len(parts) > 3 else ""
            data, status = project_snapshot(project_id)
            return self.send_json(data, status=status)
        if path.startswith("/api/file"):
            return self.send_file_preview(parsed.query)
        if path.startswith("/media/"):
            return self.serve_media(path)
        return self.serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs/start":
            return self.send_json({"job": job_summary(start_job(self.read_body_json()))})
        if parsed.path == "/api/review/rewrite":
            return self._handle_review_rewrite()
        if parsed.path == "/api/review/apply":
            return self._handle_review_apply()
        if parsed.path == "/api/system/health-check":
            return self._handle_health_check()
        if parsed.path == "/api/system/check-data-link":
            payload = self.read_body_json()
            payload["job_kind"] = "data_link_check"
            return self.send_json({"job": job_summary(start_job(payload))})
        if parsed.path == "/api/system/self-check":
            payload = self.read_body_json()
            payload["job_kind"] = "controller_self_check"
            return self.send_json({"job": job_summary(start_job(payload))})
        if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/stop"):
            job = JOBS.get(parsed.path.split("/")[3])
            if not job:
                return self.send_json({"error": "job not found"}, status=404)
            if job.process and job.process.poll() is None:
                job.process.terminate()
                job.status = "stopping"
                job.publish("job_stopping", {"message": "terminate requested"})
            return self.send_json({"job": job_summary(job)})
        if parsed.path.startswith("/api/projects/") and parsed.path.endswith("/archive"):
            parts = parsed.path.split("/")
            project_id = parts[3] if len(parts) > 3 else ""
            data, status = archive_project(project_id)
            return self.send_json(data, status=status)
        return self.send_json({"error": "not found"}, status=404)

    def read_body_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle_health_check(self) -> None:
        try:
            health_check = import_module("00_main_controller.health_check")
            result = health_check.run_health_check()
            self.send_json(result)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def _handle_review_rewrite(self) -> None:
        try:
            payload = self.read_body_json()
            result_rewriter = import_module("00_common.result_rewriter")
            result = result_rewriter.rewrite_module_result(
                run_dir_raw=str(payload.get("run_dir") or ""),
                module_name=str(payload.get("module_name") or payload.get("module") or ""),
                user_note=str(payload.get("user_note") or payload.get("note") or ""),
            )
            self.send_json(result, status=200)
        except Exception as exc:
            self.send_json({"status": "failed", "error": str(exc)}, status=500)

    def _handle_review_apply(self) -> None:
        try:
            payload = self.read_body_json()
            result_rewriter = import_module("00_common.result_rewriter")
            result = result_rewriter.apply_reviewed_result(
                run_dir_raw=str(payload.get("run_dir") or ""),
                module_name=str(payload.get("module_name") or payload.get("module") or ""),
                reviewed_path_raw=str(payload.get("reviewed_path") or ""),
            )
            self.send_json(result, status=200)
        except Exception as exc:
            self.send_json({"status": "failed", "error": str(exc)}, status=500)

    def _handle_module_requirements(self, params: dict[str, str]) -> None:
        try:
            module_contracts_mod = import_module("00_common.module_contracts")
            module_name = params.get("module", "")
            run_dir_str = params.get("run_dir", "")
            if not module_name:
                self.send_json({"error": "module parameter required"}, status=400)
                return
            if run_dir_str:
                run_path = WORKSPACE_DIR / run_dir_str if not Path(run_dir_str).is_absolute() else Path(run_dir_str)
            else:
                projects_dir = WORKSPACE_DIR / "projects"
                project_dirs = sorted(projects_dir.iterdir()) if projects_dir.exists() else []
                run_path = project_dirs[-1] if project_dirs else WORKSPACE_DIR
            contracts = module_contracts_mod.load_contracts()
            result = module_contracts_mod.inspect_module_requirements(run_path, module_name, contracts)
            self.send_json(result)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def stream_events(self, job_id: str) -> None:
        job = JOBS.get(job_id)
        if not job:
            return self.send_json({"error": "job not found"}, status=404)
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue()
        with job.lock:
            job.subscribers.append(subscriber)
            backlog = list(job.events[-100:])
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            for event in backlog:
                self.write_sse(event)
            while True:
                try:
                    self.write_sse(subscriber.get(timeout=15))
                except queue.Empty:
                    self.wfile.write(b"event: ping\ndata: {}\n\n")
                    self.wfile.flush()
        except Exception:
            pass
        finally:
            with job.lock:
                if subscriber in job.subscribers:
                    job.subscribers.remove(subscriber)

    def write_sse(self, event: dict[str, Any]) -> None:
        raw = f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(raw)
        self.wfile.flush()

    def send_file_preview(self, query: str) -> None:
        rel = parse_qs(query).get("path", [""])[0]
        path = (ROOT_DIR / safe_rel_path(rel)).resolve()
        if not path.exists() or not path.is_file() or ROOT_DIR.resolve() not in path.parents:
            return self.send_json({"error": "file not found"}, status=404)
        suffix = path.suffix.lower()
        max_preview_bytes = 2 * 1024 * 1024
        if suffix == ".json":
            file_size = path.stat().st_size
            truncated = file_size > max_preview_bytes
            if truncated:
                raw_bytes = path.read_bytes()[:max_preview_bytes]
                try:
                    content = json.loads(raw_bytes.decode("utf-8", errors="replace"))
                except Exception:
                    content = raw_bytes.decode("utf-8", errors="replace")
            else:
                content = read_json(path, {})
            result = {"path": rel, "type": "json", "content": content}
            if truncated:
                result["truncated"] = True
                result["original_size"] = file_size
            return self.send_json(result)
        if suffix in {".txt", ".md", ".log", ".srt", ".ass"}:
            content = ""
            for encoding in ("utf-8", "utf-8-sig", "gb18030"):
                try:
                    content = path.read_text(encoding=encoding, errors="replace")
                    break
                except Exception:
                    pass
            truncated = len(content) > 200000
            result = {"path": rel, "type": "text", "content": repair_mojibake_text(content)[-200000:]}
            if truncated:
                result["truncated"] = True
            return self.send_json(result)
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            return self.send_json({"path": rel, "type": "image", "url": "/media/" + rel})
        if suffix in {".wav", ".mp4"}:
            return self.send_json({"path": rel, "type": "media", "url": "/media/" + rel, "size": path.stat().st_size})
        return self.send_json({"path": rel, "type": "binary", "size": path.stat().st_size})

    def serve_media(self, path: str) -> None:
        rel = path.replace("/media/", "", 1)
        file_path = (ROOT_DIR / safe_rel_path(rel)).resolve()
        workspace_resolved = WORKSPACE_DIR.resolve()
        if not file_path.exists() or not file_path.is_file() or (workspace_resolved != file_path and workspace_resolved not in file_path.parents):
            return self.send_json({"error": "media not found"}, status=404)
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TEXT_MIME.get(file_path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def serve_static(self, path: str) -> None:
        rel = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = WEB_DIR / "static" / safe_rel_path(rel)
        if not file_path.exists() or not file_path.is_file():
            file_path = WEB_DIR / "static" / "index.html"
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TEXT_MIME.get(file_path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Short Drama 00-10 Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1144)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Web UI running: http://{args.host}:{args.port}")
    print("00-10 controller, data-link check, pipeline runner, artifacts preview are enabled.")
    print("Text LLM defaults to DeepSeek V4 Pro. API key can be supplied by UI or AI_DRAMA_LLM_API_KEY.")
    print("UTF-8 mode is forced for child processes and SSE logs.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Web UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
