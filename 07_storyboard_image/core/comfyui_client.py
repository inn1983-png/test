from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any


class ComfyUIClient:
    """Small ComfyUI queue client.

    Supports dry_run and execute modes. execute mode can use either old global
    env injection or per-task workflow_config from workflow_router.
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

    def _load_workflow(self, workflow_path: str | None = None) -> dict[str, Any]:
        resolved = (workflow_path or self.workflow_path or "").strip()
        if not resolved:
            raise RuntimeError("workflow_path is required when AI_DRAMA_IMAGE_EXECUTION_MODE=execute.")
        path = Path(resolved)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise RuntimeError("ComfyUI workflow JSON must be an object.")
        return data

    def _inject_node_value(self, workflow: dict[str, Any], node_id: str, value: Any, input_key: str = "text") -> None:
        node_id = str(node_id or "").strip()
        if not node_id:
            return
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            raise RuntimeError(f"ComfyUI workflow missing node id: {node_id}")
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            raise RuntimeError(f"ComfyUI node {node_id} inputs must be an object.")
        inputs[input_key] = value

    def build_workflow(self, task: dict[str, Any]) -> dict[str, Any]:
        cfg = task.get("workflow_config", {}) if isinstance(task.get("workflow_config"), dict) else {}
        workflow = self._load_workflow(str(cfg.get("workflow_path") or "") or None)
        positive = task.get("positive_prompt", "")
        negative = task.get("negative_prompt", "")
        output_name = task.get("output_basename", task.get("frame_id", task.get("task_id", "image")))
        positive_node = cfg.get("positive_node_id") or os.getenv("AI_DRAMA_COMFYUI_POSITIVE_NODE_ID", "")
        negative_node = cfg.get("negative_node_id") or os.getenv("AI_DRAMA_COMFYUI_NEGATIVE_NODE_ID", "")
        output_node = cfg.get("output_prefix_node_id") or cfg.get("output_node_id") or os.getenv("AI_DRAMA_COMFYUI_OUTPUT_PREFIX_NODE_ID", "")
        positive_input = cfg.get("positive_input") or os.getenv("AI_DRAMA_COMFYUI_POSITIVE_INPUT", "text")
        negative_input = cfg.get("negative_input") or os.getenv("AI_DRAMA_COMFYUI_NEGATIVE_INPUT", "text")
        output_input = cfg.get("output_prefix_input") or os.getenv("AI_DRAMA_COMFYUI_OUTPUT_PREFIX_INPUT", "filename_prefix")
        self._inject_node_value(workflow, str(positive_node), positive, str(positive_input))
        self._inject_node_value(workflow, str(negative_node), negative, str(negative_input))
        self._inject_node_value(workflow, str(output_node), output_name, str(output_input))
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
        output_path = str(task.get("output_image_path") or "")
        if not output_path:
            images_dir = Path(output_dir) / "images" / str(task.get("task_type", "misc"))
            images_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(images_dir / f"{task.get('output_basename', task.get('task_id', 'image'))}.png")
        else:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image_id = str(task.get("frame_id") or task.get("appearance_asset_key") or task.get("lock_key") or task.get("task_id") or "image")
        if self.dry_run:
            return {
                "status": "planned",
                "execution_mode": "dry_run",
                "prompt_id": None,
                "image_id": image_id,
                "frame_id": task.get("frame_id"),
                "task_id": task.get("task_id"),
                "output_path": output_path,
                "note": "Dry run only. Set AI_DRAMA_IMAGE_EXECUTION_MODE=execute and configure workflow mapping to generate images.",
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
            "image_id": image_id,
            "frame_id": task.get("frame_id"),
            "task_id": task.get("task_id"),
            "output_path": output_path,
            "history": history.get(str(prompt_id), {}),
        }
