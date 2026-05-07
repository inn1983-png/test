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
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
PIPELINE_FILE = ROOT_DIR / "pipeline.json"
WORKSPACE_DIR = ROOT_DIR / "workspace"

TEXT_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def safe_project_id(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "project_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    allowed = []
    for ch in raw:
        allowed.append(ch if ch.isalnum() or ch in "_-" else "_")
    return "".join(allowed).strip("_") or "project_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_rel_path(raw: str) -> Path:
    raw = unquote(raw).replace("\\", "/")
    parts = [part for part in raw.split("/") if part and part not in {".", ".."}]
    return Path(*parts) if parts else Path()


@dataclass
class Job:
    id: str
    mode: str
    project_id: str | None
    book_id: str | None
    chapter_id: str | None
    command: list[str]
    run_dir: Path
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
            if len(self.events) > 2000:
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
    return read_json(PIPELINE_FILE, {"pipeline": []})


def project_run_dir(project_id: str) -> Path:
    return WORKSPACE_DIR / "projects" / project_id


def book_chapter_run_dir(book_id: str, chapter_id: str) -> Path:
    return WORKSPACE_DIR / "books" / book_id / "chapters" / chapter_id


def discover_projects() -> list[dict[str, Any]]:
    base = WORKSPACE_DIR / "projects"
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(base.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
        if not item.is_dir():
            continue
        status = read_json(item / "run_status.json", {})
        rows.append(
            {
                "project_id": item.name,
                "run_dir": str(item.relative_to(ROOT_DIR)),
                "updated_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat(timespec="seconds"),
                "status": summarize_run_status(status),
            }
        )
    return rows[:100]


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


def discover_run_snapshot(run_dir: Path) -> dict[str, Any]:
    status = read_json(run_dir / "run_status.json", {})
    pipeline = load_pipeline().get("pipeline", [])
    modules: list[dict[str, Any]] = []
    for module_name in pipeline:
        module_dir = run_dir / module_name
        module_status = (status.get("modules", {}) or {}).get(module_name, {}) if isinstance(status, dict) else {}
        modules.append(
            {
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
                "quality": discover_quality(module_dir),
            }
        )
    return {
        "run_dir": str(run_dir.relative_to(ROOT_DIR)) if run_dir.exists() or ROOT_DIR in run_dir.parents else str(run_dir),
        "run_status": status,
        "summary_status": summarize_run_status(status),
        "modules": modules,
        "important_outputs": discover_important_outputs(run_dir),
    }


def discover_module_outputs(module_dir: Path) -> list[dict[str, Any]]:
    if not module_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(module_dir.glob("*.json")):
        rows.append(file_row(path))
    return rows


def discover_stage_outputs(module_dir: Path) -> list[dict[str, Any]]:
    inter = module_dir / "intermediate"
    if not inter.exists():
        return []
    rows = [file_row(path) for path in sorted(inter.glob("*.json"))]
    for row in rows:
        data = read_json(ROOT_DIR / row["path"], {})
        if isinstance(data, dict):
            quality = data.get("stage_quality") or {}
            row["stage_id"] = data.get("stage") or data.get("stage_id") or row["name"].split("_")[0]
            row["score"] = quality.get("score") if isinstance(quality, dict) else None
            row["passed"] = quality.get("passed") if isinstance(quality, dict) else None
            row["issues_count"] = len(quality.get("issues", [])) if isinstance(quality, dict) and isinstance(quality.get("issues"), list) else 0
        else:
            row["stage_id"] = row["name"].split("_")[0]
    return rows


def discover_quality(module_dir: Path) -> dict[str, Any]:
    candidates = list(module_dir.glob("*.json"))
    for path in candidates:
        data = read_json(path, {})
        if isinstance(data, dict) and isinstance(data.get("quality_report"), dict):
            return data["quality_report"]
    return {}


def discover_important_outputs(run_dir: Path) -> list[dict[str, Any]]:
    names = [
        "01_novel_parser/novel_analysis.json",
        "02_script_writer/script.json",
        "03_character_system/characters.json",
        "04_scene_system/scenes.json",
        "05_prop_system/props.json",
        "06_storyboard/storyboard.json",
        "06_storyboard/storyboard_meta.json",
        "07_storyboard_image/image_manifest.json",
        "08_audio/final_audio.wav",
        "09_video/video_manifest.json",
        "10_final_assembly/final.mp4",
    ]
    rows = []
    for name in names:
        path = run_dir / name
        if path.exists():
            rows.append(file_row(path))
    return rows


def file_row(path: Path) -> dict[str, Any]:
    try:
        rel = path.relative_to(ROOT_DIR)
    except ValueError:
        rel = path
    return {
        "name": path.name,
        "path": str(rel).replace("\\", "/"),
        "size": path.stat().st_size if path.exists() else 0,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,
    }


def build_command(payload: dict[str, Any], run_dir: Path) -> tuple[list[str], dict[str, str]]:
    mode = payload.get("mode") or "project"
    cmd = [sys.executable, str(ROOT_DIR / "00_main_controller" / "run_pipeline.py"), "--mode", mode]
    env = os.environ.copy()

    if mode == "book_chapter":
        book_id = safe_project_id(payload.get("book_id") or "book_demo")
        chapter_id = safe_project_id(payload.get("chapter_id") or "chapter_001")
        cmd.extend(["--book-id", book_id, "--chapter-id", chapter_id])
    else:
        project_id = safe_project_id(payload.get("project_id"))
        cmd.extend(["--project-id", project_id])

    if payload.get("from_module"):
        cmd.extend(["--from-module", str(payload["from_module"])])
    if payload.get("only_module"):
        cmd.extend(["--only-module", str(payload["only_module"])])
    if payload.get("skip_validation"):
        cmd.append("--skip-validation")
    if payload.get("skip_dependency_check"):
        cmd.append("--skip-dependency-check")
    if payload.get("strict_order", True):
        cmd.append("--strict-order")

    llm_base_url = str(payload.get("llm_base_url") or "").strip()
    llm_model = str(payload.get("llm_model") or "").strip()
    llm_temperature = str(payload.get("llm_temperature") or "").strip()
    llm_timeout = str(payload.get("llm_timeout_sec") or "").strip()
    if llm_base_url:
        env["AI_DRAMA_LLM_BASE_URL"] = llm_base_url
    if llm_model:
        env["AI_DRAMA_LLM_MODEL"] = llm_model
    if llm_temperature:
        env["AI_DRAMA_LLM_TEMPERATURE"] = llm_temperature
    if llm_timeout:
        env["AI_DRAMA_LLM_TIMEOUT_SEC"] = llm_timeout

    return cmd, env


def start_job(payload: dict[str, Any]) -> Job:
    mode = payload.get("mode") or "project"
    if mode == "book_chapter":
        book_id = safe_project_id(payload.get("book_id") or "book_demo")
        chapter_id = safe_project_id(payload.get("chapter_id") or "chapter_001")
        run_dir = book_chapter_run_dir(book_id, chapter_id)
        project_id = None
    else:
        project_id = safe_project_id(payload.get("project_id"))
        book_id = None
        chapter_id = None
        run_dir = project_run_dir(project_id)

    novel_text = str(payload.get("novel_text") or "").strip()
    if novel_text:
        write_text(run_dir / "input" / "novel.txt", novel_text)

    cmd, env = build_command(payload, run_dir)
    job = Job(
        id=uuid.uuid4().hex[:12],
        mode=mode,
        project_id=project_id,
        book_id=book_id,
        chapter_id=chapter_id,
        command=cmd,
        run_dir=run_dir,
    )
    JOBS.add(job)
    thread = threading.Thread(target=run_job_thread, args=(job, env), daemon=True)
    thread.start()
    return job


def run_job_thread(job: Job, env: dict[str, str]) -> None:
    job.status = "running"
    job.publish("job_started", {"command": job.command, "run_dir": str(job.run_dir.relative_to(ROOT_DIR))})
    try:
        process = subprocess.Popen(
            job.command,
            cwd=str(ROOT_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        job.process = process
        assert process.stdout is not None
        last_snapshot = 0.0
        for line in process.stdout:
            clean = line.rstrip("\n")
            if clean:
                job.publish("log", {"line": clean})
            if time.time() - last_snapshot > 2.0:
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
        if path == "/api/jobs":
            return self.send_json({"jobs": [job_summary(job) for job in JOBS.list()]})
        if path.startswith("/api/jobs/") and path.endswith("/events"):
            job_id = path.split("/")[3]
            return self.stream_events(job_id)
        if path.startswith("/api/jobs/") and path.endswith("/snapshot"):
            job_id = path.split("/")[3]
            job = JOBS.get(job_id)
            if not job:
                return self.send_json({"error": "job not found"}, status=404)
            return self.send_json({"job": job_summary(job), "snapshot": discover_run_snapshot(job.run_dir)})
        if path.startswith("/api/file"):
            return self.send_file_preview(parsed.query)
        return self.serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/jobs/start":
            payload = self.read_body_json()
            job = start_job(payload)
            return self.send_json({"job": job_summary(job)})
        if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/stop"):
            job_id = parsed.path.split("/")[3]
            job = JOBS.get(job_id)
            if not job:
                return self.send_json({"error": "job not found"}, status=404)
            if job.process and job.process.poll() is None:
                job.process.terminate()
                job.status = "stopping"
                job.publish("job_stopping", {"message": "terminate requested"})
            return self.send_json({"job": job_summary(job)})
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
                    event = subscriber.get(timeout=15)
                    self.write_sse(event)
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
        params = parse_qs(query)
        rel = params.get("path", [""])[0]
        path = ROOT_DIR / safe_rel_path(rel)
        if not path.exists() or not path.is_file() or ROOT_DIR not in path.resolve().parents:
            return self.send_json({"error": "file not found"}, status=404)
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self.send_json({"path": rel, "type": "json", "content": read_json(path, {})})
        if suffix in {".txt", ".md", ".log"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            return self.send_json({"path": rel, "type": "text", "content": text[-200000:]})
        return self.send_json({"path": rel, "type": "binary", "size": path.stat().st_size})

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


def job_summary(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "mode": job.mode,
        "project_id": job.project_id,
        "book_id": job.book_id,
        "chapter_id": job.chapter_id,
        "run_dir": str(job.run_dir.relative_to(ROOT_DIR)) if ROOT_DIR in job.run_dir.parents else str(job.run_dir),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "status": job.status,
        "return_code": job.return_code,
        "command": job.command,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Short Drama final Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Web UI running: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Web UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
