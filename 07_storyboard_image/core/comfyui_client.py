from __future__ import annotations

import base64
import json
import os
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


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
        self.comfyui_output_dir = os.getenv("AI_DRAMA_COMFYUI_OUTPUT_DIR", os.getenv("COMFYUI_OUTPUT_DIR", "")).strip()

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

    def _write_dry_run_placeholder(self, output_path: str, task: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            path.write_bytes(PLACEHOLDER_PNG)
            meta_path = path.with_suffix(path.suffix + ".dry_run.json")
            meta_path.write_text(
                json.dumps(
                    {
                        "status": "planned",
                        "execution_mode": "dry_run",
                        "task_type": task.get("task_type"),
                        "frame_id": task.get("frame_id"),
                        "task_id": task.get("task_id"),
                        "positive_prompt": task.get("positive_prompt", ""),
                        "negative_prompt": task.get("negative_prompt", ""),
                        "note": "This is a 1x1 placeholder image created so downstream dry-run modules can validate file paths.",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            path.write_text("DRY_RUN_PLACEHOLDER_IMAGE\n", encoding="utf-8")

    def _extract_history_outputs(self, history_item: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        outputs = history_item.get("outputs", {}) if isinstance(history_item, dict) else {}
        if not isinstance(outputs, dict):
            return rows
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue
            for key in ("images", "gifs", "videos"):
                values = node_output.get(key, [])
                if not isinstance(values, list):
                    continue
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    rows.append(
                        {
                            "node_id": str(node_id),
                            "kind": key,
                            "filename": value.get("filename"),
                            "subfolder": value.get("subfolder", ""),
                            "type": value.get("type", ""),
                        }
                    )
        return rows

    def _history_candidate_paths(self, history_outputs: list[dict[str, Any]]) -> list[Path]:
        if not self.comfyui_output_dir:
            return []
        root = Path(self.comfyui_output_dir)
        candidates: list[Path] = []
        for item in history_outputs:
            filename = item.get("filename")
            if not isinstance(filename, str) or not filename:
                continue
            subfolder = item.get("subfolder")
            if isinstance(subfolder, str) and subfolder:
                candidates.append(root / subfolder / filename)
            candidates.append(root / filename)
        return candidates

    def _find_latest_matching_output(self, output_basename: str, submit_time: float, history_outputs: list[dict[str, Any]]) -> Path | None:
        for candidate in self._history_candidate_paths(history_outputs):
            if candidate.exists() and candidate.is_file():
                return candidate
        if not self.comfyui_output_dir:
            return None
        root = Path(self.comfyui_output_dir)
        if not root.exists():
            return None
        basename = Path(output_basename).stem
        matches: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if basename and basename not in path.stem:
                continue
            try:
                if path.stat().st_mtime < submit_time - 5:
                    continue
            except OSError:
                continue
            matches.append(path)
        if not matches:
            return None
        return max(matches, key=lambda item: item.stat().st_mtime)

    def _write_resolution_report(self, output_dir: str | Path, record: dict[str, Any]) -> None:
        path = Path(output_dir) / "output_resolution_report.json"
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", "1.0")
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        records = data.setdefault("records", [])
        if not isinstance(records, list):
            records = []
            data["records"] = records
        records.append(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def submit_task(self, task: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
        output_path = str(task.get("output_image_path") or "")
        if not output_path:
            images_dir = Path(output_dir) / "images" / str(task.get("task_type", "misc"))
            images_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(images_dir / f"{task.get('output_basename', task.get('task_id', 'image'))}.png")
        else:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image_id = str(task.get("frame_id") or task.get("appearance_asset_key") or task.get("lock_key") or task.get("task_id") or "image")
        output_basename = str(task.get("output_basename") or Path(output_path).stem)
        cfg = task.get("workflow_config", {}) if isinstance(task.get("workflow_config"), dict) else {}
        workflow_path = str(cfg.get("workflow_path") or self.workflow_path or "")
        if self.dry_run:
            self._write_dry_run_placeholder(output_path, task)
            return {
                "status": "planned",
                "execution_mode": "dry_run",
                "prompt_id": None,
                "image_id": image_id,
                "frame_id": task.get("frame_id"),
                "task_id": task.get("task_id"),
                "output_path": output_path,
                "note": "Dry-run placeholder image written. Set AI_DRAMA_IMAGE_EXECUTION_MODE=execute and configure workflow mapping to generate real images.",
            }
        workflow = self.build_workflow(task)
        submit_time = time.time()
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
        expected_path = Path(output_path)
        output_exists = expected_path.exists()
        history_item = history.get(str(prompt_id), {})
        history_outputs = self._extract_history_outputs(history_item if isinstance(history_item, dict) else {})
        resolved_from: str | None = None
        if not output_exists:
            found = self._find_latest_matching_output(output_basename, submit_time, history_outputs)
            if found:
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(found, expected_path)
                output_exists = expected_path.exists()
                resolved_from = str(found)
        error = None
        if not output_exists:
            error = (
                "ComfyUI finished but image output was not found. "
                f"expected_output_path={output_path}; output_basename={output_basename}; "
                f"history_outputs={history_outputs}; "
                "check workflow SaveImage filename_prefix/output node mapping."
            )
        self._write_resolution_report(
            output_dir,
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "status": "success" if output_exists else "failed",
                "prompt_id": prompt_id,
                "image_id": image_id,
                "frame_id": task.get("frame_id"),
                "task_id": task.get("task_id"),
                "expected_output_path": output_path,
                "output_basename": output_basename,
                "workflow_path": workflow_path,
                "submit_time": submit_time,
                "history_outputs": history_outputs,
                "resolved_from": resolved_from,
                "comfyui_output_dir": self.comfyui_output_dir,
                "error": error,
            },
        )
        return {
            "status": "success" if output_exists else "failed",
            "execution_mode": "execute",
            "prompt_id": prompt_id,
            "image_id": image_id,
            "frame_id": task.get("frame_id"),
            "task_id": task.get("task_id"),
            "output_path": output_path,
            "history": history_item,
            "history_outputs": history_outputs,
            "resolved_from": resolved_from,
            "error": error,
        }
