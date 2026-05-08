from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from backend.agents.director_agent import init_project, next_step, run_until_idle
from backend.agents.reviewer_agent import review_node
from backend.agents.repair_agent import repair_node
from backend.app.canvas_store import load_canvas, refresh_canvas
from backend.app.node_store import list_nodes, load_node, update_node
from backend.app.project_store import list_projects, load_project, save_project
from backend.app.settings_store import load_settings, save_settings
from backend.app.task_store import list_tasks, enqueue_node_task
from backend.app.workflow_store import list_workflows, save_workflow
from backend.workers.task_runner import run_pending


def runtime_snapshot(project_id: str) -> dict:
    return {
        "project": load_project(project_id),
        "settings": load_settings(project_id),
        "canvas": load_canvas(project_id),
        "nodes": list_nodes(project_id),
        "tasks": list_tasks(project_id),
        "workflows": list_workflows(project_id),
    }


def run_cli(command: str, project_id: str) -> None:
    if command == "init":
        init_project(project_id)
    elif command == "step":
        next_step(project_id)
        run_pending(project_id)
    elif command == "run":
        run_until_idle(project_id)
    print(json.dumps(runtime_snapshot(project_id), ensure_ascii=False, indent=2))


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        text = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(text or "{}")

    def do_OPTIONS(self):
        self._json({"ok": True})

    def do_GET(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        try:
            if parts == ["api", "projects"]:
                self._json({"projects": list_projects()})
                return
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
                project_id = parts[2]
                if len(parts) == 3:
                    self._json(runtime_snapshot(project_id)); return
                area = parts[3]
                if area == "canvas":
                    self._json(load_canvas(project_id)); return
                if area == "settings":
                    self._json(load_settings(project_id)); return
                if area == "workflows":
                    self._json({"workflows": list_workflows(project_id)}); return
                if area == "nodes":
                    if len(parts) == 4:
                        self._json({"nodes": list_nodes(project_id)}); return
                    self._json(load_node(project_id, parts[4])); return
                if area == "tasks":
                    self._json({"tasks": list_tasks(project_id)}); return
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def do_POST(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        try:
            if len(parts) >= 4 and parts[0] == "api" and parts[1] == "projects":
                project_id = parts[2]
                action = parts[3]
                if action == "init": self._json(init_project(project_id)); return
                if action == "step":
                    next_step(project_id); run_pending(project_id); self._json(runtime_snapshot(project_id)); return
                if action == "run": self._json(run_until_idle(project_id)); return
                if action == "refresh": self._json(refresh_canvas(project_id)); return
                if action == "tasks" and len(parts) >= 6:
                    task_id = parts[4]
                    task_action = parts[5]
                    from backend.app.task_actions import retry_task, cancel_task, read_log
                    if task_action == "retry": self._json(retry_task(project_id, task_id)); return
                    if task_action == "cancel": self._json(cancel_task(project_id, task_id)); return
                    if task_action == "log": self._json({"log": read_log(project_id, task_id)}); return
                if action == "nodes" and len(parts) >= 6:
                    node_id = parts[4]
                    node_action = parts[5]
                    node = load_node(project_id, node_id)
                    if node_action == "rerun":
                        task_type = "image_generate" if node.get("type") == "shot" else "grid_build"
                        executor = "image_executor" if node.get("type") == "shot" else "grid_executor"
                        update_node(project_id, node_id, {"status": "waiting"})
                        self._json(enqueue_node_task(project_id, node_id, task_type, executor)); return
                    if node_action == "review": self._json(review_node(project_id, node_id)); return
                    if node_action == "repair": self._json(repair_node(project_id, node_id)); return
                    if node_action == "lock": self._json(update_node(project_id, node_id, {"locked": True, "status": "locked"})); return
                if action == "workflows":
                    data = self._body()
                    self._json(save_workflow(project_id, data["category"], data["name"], data["content"])); return
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def do_PATCH(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        try:
            data = self._body()
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "projects" and parts[3] == "nodes":
                self._json(update_node(parts[2], parts[4], data)); return
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "projects" and parts[3] == "settings":
                settings = load_settings(parts[2]); settings.update(data); self._json(save_settings(parts[2], settings)); return
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "projects":
                project = load_project(parts[2]); project.update(data); self._json(save_project(parts[2], project)); return
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)


def run_server(host="127.0.0.1", port=7860):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Agent Canvas API running at http://{host}:{port}")
    server.serve_forever()
