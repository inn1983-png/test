from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any


class ComfyUIClient:
    """Small ComfyUI queue client.

    The module supports two modes:
    - dry_run: write deterministic placeholder task records without contacting ComfyUI.
    - execute: submit workflow JSON to ComfyUI /prompt and poll /history.

    Workflow templating is intentionally conservative: the project can pass an
    already-exported ComfyUI API workflow JSON through AI_DRAMA_COMFYUI_WORKFLOW.
    Text/image injection is handled through node-id environment variables so the
    workflow can be changed without changing the module contract.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("AI_DRAMA_COMFYUI_BASE_URL", "http://127.0.0.1:8188").rstrip("/")
        self.workflow_path = os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", "").strip()
        self.timeout_sec = int(os.getenv("AI_DRAMA_COMFYUI_TIMEOUT_SEC", "1800"))
        self.poll_interval_sec = float(os.getenv("AI_DRAMA_COMFYUI_POLL_INTERVAL_SEC", "2"))
        self.client_id = os.getenv("AI_DRAMA_COMFYUI_CLIENT_ID", "ai_drama_07_storyboard_image")
        self.mode = os.getenv("AI_DRAMA_IMAGE_EXECUTION_MODE", "dry_run").strip().lower()

    @property
    def dry_run(self) -> bool:
        return self.mode not in {"execute", "comfyui", "real"}

    def _load_workflow(self) -> dict[str, Any]:
        if not self.workflow_path:
            raise RuntimeError("AI_DRAMA_COMFYUI_WORKFLOW is required when AI_DRAMA_IMAGE_EXECUTION_MODE=execute.")
        path = Path(self.workflow_path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise RuntimeError("ComfyUI workflow JSON must be an object.")
        return data

    def _inject_node_value(self, workflow: dict[str, Any], env_key: str, value: Any, input_key: str = "text") -> None:
        node_id = os.getenv(env_key, "").strip()
        if not node_id:
            return
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            raise RuntimeError(f"ComfyUI workflow missing node id from {env_key}: {node_id}")
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            raise RuntimeError(f"ComfyUI node {node_id} inputs must be an object.")
        inputs[input_key] = value

    def build_workflow(self, task: dict[str, Any]) -> dict[str, Any]:
        workflow = self._load_workflow()
        positive = task.get("positive_prompt", "")
        negative = task.get("negative_prompt", "")
        output_name = task.get("output_basename", task.get("frame_id", "shot"))
        self._inject_node_value(workflow, "AI_DRAMA_COMFYUI_POSITIVE_NODE_ID", positive, os.getenv("AI_DRAMA_COMFYUI_POSITIVE_INPUT", "text"))
        self._inject_node_value(workflow, "AI_DRAMA_COMFYUI_NEGATIVE_NODE_ID", negative, os.getenv("AI_DRAMA_COMFYUI_NEGATIVE_INPUT", "text"))
        self._inject_node_value(workflow, "AI_DRAMA_COMFYUI_OUTPUT_PREFIX_NODE_ID", output_name, os.getenv("AI_DRAMA_COMFYUI_OUTPUT_PREFIX_INPUT", "filename_prefix"))
        return workflow

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError(f"ComfyUI {path} response must be an object.")
        return value

    def _get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=self.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError(f"ComfyUI {path} response must be an object.")
        return value

    def submit_task(self, task: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
        images_dir = Path(output_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        frame_id = str(task.get("frame_id") or task.get("task_id") or "shot")
        output_path = images_dir / f"{task.get('output_basename', frame_id)}.png"
        if self.dry_run:
            return {
                "status": "planned",
                "execution_mode": "dry_run",
                "prompt_id": None,
                "frame_id": frame_id,
                "output_path": str(output_path),
                "note": "Dry run only. Set AI_DRAMA_IMAGE_EXECUTION_MODE=execute and configure ComfyUI workflow/node ids to generate images.",
            }

        workflow = self.build_workflow(task)
        response = self._post_json("/prompt", {"prompt": workflow, "client_id": self.client_id})
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {response}")
        deadline = time.time() + self.timeout_sec
        history: dict[str, Any] = {}
        while time.time() < deadline:
            history = self._get_json(f"/history/{prompt_id}")
            if str(prompt_id) in history:
                break
            time.sleep(self.poll_interval_sec)
        if str(prompt_id) not in history:
            raise TimeoutError(f"ComfyUI prompt timeout: {prompt_id}")
        return {
            "status": "submitted",
            "execution_mode": "execute",
            "prompt_id": prompt_id,
            "frame_id": frame_id,
            "output_path": str(output_path),
            "history": history.get(str(prompt_id), {}),
        }
