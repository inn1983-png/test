from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from importlib import import_module
from pathlib import Path
from typing import Any

workflow_adapter = import_module("09_video.core.workflow_adapter")


class ComfyUIClient:
    """ComfyUI queue client for one-submit-per-window LTX2.3 execution."""

    def __init__(self) -> None:
        self.base_url = os.getenv("AI_DRAMA_COMFYUI_BASE_URL", "http://127.0.0.1:8188").rstrip("/")
        self.workflow_path = os.getenv("AI_DRAMA_VIDEO_COMFYUI_WORKFLOW", os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", "")).strip()
        self.timeout_sec = int(os.getenv("AI_DRAMA_VIDEO_COMFYUI_TIMEOUT_SEC", os.getenv("AI_DRAMA_COMFYUI_TIMEOUT_SEC", "3600")))
        self.poll_interval_sec = float(os.getenv("AI_DRAMA_COMFYUI_POLL_INTERVAL_SEC", "2"))
        self.client_id = os.getenv("AI_DRAMA_COMFYUI_CLIENT_ID", "ai_drama_09_video_ltx23")
        self.mode = os.getenv("AI_DRAMA_VIDEO_EXECUTION_MODE", "dry_run").strip().lower()
        self.ffmpeg = os.getenv("AI_DRAMA_FFMPEG", "ffmpeg")

    @property
    def dry_run(self) -> bool:
        return self.mode not in {"execute", "comfyui", "real"}

    def _load_workflow(self) -> dict[str, Any]:
        if not self.workflow_path:
            raise RuntimeError("AI_DRAMA_VIDEO_COMFYUI_WORKFLOW or AI_DRAMA_COMFYUI_WORKFLOW is required in execute mode.")
        with Path(self.workflow_path).open("r", encoding="utf-8") as f:
            value = json.load(f)
        if not isinstance(value, dict):
            raise RuntimeError("ComfyUI workflow API JSON must be an object.")
        return value

    def _inject_node_value(self, workflow: dict[str, Any], node_id: str, value: Any, input_key: str) -> None:
        node_id = str(node_id or "").strip()
        if not node_id:
            return
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            raise RuntimeError(f"ComfyUI workflow missing node id: {node_id}")
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            raise RuntimeError(f"ComfyUI node {node_id} inputs must be an object.")
        inputs[str(input_key)] = value

    def _inject_from_env(self, workflow: dict[str, Any], payload: dict[str, Any]) -> None:
        mapping = {
            "prompt": "AI_DRAMA_VIDEO_NODE_PROMPT",
            "negative_prompt": "AI_DRAMA_VIDEO_NODE_NEGATIVE_PROMPT",
            "image_path": "AI_DRAMA_VIDEO_NODE_IMAGE_PATH",
            "audio_path": "AI_DRAMA_VIDEO_NODE_AUDIO_PATH",
            "project_name": "AI_DRAMA_VIDEO_NODE_PROJECT_NAME",
            "base_path": "AI_DRAMA_VIDEO_NODE_BASE_PATH",
            "current_segment_index": "AI_DRAMA_VIDEO_NODE_CURRENT_SEGMENT_INDEX",
            "current_chunk": "AI_DRAMA_VIDEO_NODE_CURRENT_CHUNK",
            "duration": "AI_DRAMA_VIDEO_NODE_DURATION",
            "fps": "AI_DRAMA_VIDEO_NODE_FPS",
            "width": "AI_DRAMA_VIDEO_NODE_WIDTH",
            "height": "AI_DRAMA_VIDEO_NODE_HEIGHT",
            "frame_count": "AI_DRAMA_VIDEO_NODE_FRAME_COUNT",
            "overlap_frames": "AI_DRAMA_VIDEO_NODE_OVERLAP_FRAMES",
            "window_size": "AI_DRAMA_VIDEO_NODE_WINDOW_SIZE",
            "stride": "AI_DRAMA_VIDEO_NODE_STRIDE",
            "output_basename": "AI_DRAMA_VIDEO_NODE_OUTPUT_PREFIX",
        }
        for idx in range(1, 10):
            mapping[f"image_{idx}"] = f"AI_DRAMA_VIDEO_NODE_IMAGE_{idx}"
        for payload_key, env_name in mapping.items():
            spec = os.getenv(env_name, "").strip()
            if not spec:
                continue
            if ":" not in spec:
                raise RuntimeError(f"{env_name} must be node_id:input_key, got {spec!r}")
            node_id, input_key = spec.split(":", 1)
            value = payload.get(payload_key)
            if payload_key == "current_chunk" and value is None:
                value = payload.get("current_segment_index", 1)
            self._inject_node_value(workflow, node_id, value, input_key)

    def build_workflow(self, segment: dict[str, Any]) -> dict[str, Any]:
        workflow = self._load_workflow()
        payload = workflow_adapter.build_comfyui_workflow_payload(segment)
        self._inject_from_env(workflow, payload)
        return workflow

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError(f"ComfyUI {path} response must be object.")
        return value

    def _get_json(self, path: str) -> dict[str, Any]:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=self.timeout_sec) as response:
            raw = response.read().decode("utf-8")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError(f"ComfyUI {path} response must be object.")
        return value

    def _first_existing_image(self, segment: dict[str, Any]) -> Path | None:
        for image_path in segment.get("image_paths", []) or []:
            path = Path(str(image_path))
            if path.exists():
                return path
        path = Path(str(segment.get("image_path") or ""))
        return path if path.exists() else None

    def _make_dry_run_clip(self, segment: dict[str, Any]) -> str:
        output_path = Path(str(segment.get("output_clip_path")))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(float(segment.get("duration_seconds") or 1.0), 0.1)
        image_path = self._first_existing_image(segment)
        audio_path = Path(str(segment.get("audio_source_path") or ""))
        if shutil.which(self.ffmpeg) and image_path and audio_path.exists():
            cmd = [
                self.ffmpeg,
                "-y",
                "-loop",
                "1",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(image_path),
                "-i",
                str(audio_path),
                "-ss",
                f"{float(segment.get('start_seconds') or 0):.3f}",
                "-t",
                f"{duration:.3f}",
                "-vf",
                f"scale={int(segment.get('width') or 1280)}:{int(segment.get('height') or 720)}:force_original_aspect_ratio=decrease,pad={int(segment.get('width') or 1280)}:{int(segment.get('height') or 720)}:(ow-iw)/2:(oh-ih)/2",
                "-r",
                str(float(segment.get("fps") or 24)),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode == 0 and output_path.exists():
                return str(output_path)
        output_path.write_text(
            "DRY_RUN_PLACEHOLDER_MP4\n"
            f"segment_id={segment.get('segment_id')}\n"
            f"frame_ids={segment.get('frame_ids')}\n"
            f"image_paths={segment.get('image_paths')}\n"
            f"audio={segment.get('audio_source_path')}\n"
            f"prompt={segment.get('ltx_prompt')}\n"
            f"start={segment.get('start_seconds')} end={segment.get('end_seconds')}\n",
            encoding="utf-8",
        )
        return str(output_path)

    def submit_segment(self, segment: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
        output_path = Path(str(segment.get("output_clip_path") or Path(output_dir) / "clips" / f"{segment.get('segment_id')}.mp4"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and os.getenv("AI_DRAMA_VIDEO_FORCE_RERUN", "0") not in {"1", "true", "yes", "on"}:
            return {
                "status": "success",
                "execution_mode": segment.get("execution_mode", "dry_run"),
                "resume_hit": True,
                "prompt_id": None,
                "segment_id": segment.get("segment_id"),
                "output_clip_path": str(output_path),
                "note": "Existing clip found; skipped by breakpoint resume.",
            }
        if self.dry_run:
            clip = self._make_dry_run_clip({**segment, "output_clip_path": str(output_path)})
            return {
                "status": "success",
                "execution_mode": "dry_run",
                "resume_hit": False,
                "prompt_id": None,
                "segment_id": segment.get("segment_id"),
                "output_clip_path": clip,
                "note": "Dry run clip generated for one keyframe window. Set AI_DRAMA_VIDEO_EXECUTION_MODE=execute and workflow node mappings to run LTX2.3 ComfyUI.",
            }
        workflow = self.build_workflow(segment)
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
            "status": "success" if output_path.exists() else "submitted",
            "execution_mode": "execute",
            "resume_hit": False,
            "prompt_id": prompt_id,
            "segment_id": segment.get("segment_id"),
            "output_clip_path": str(output_path),
            "history": history.get(str(prompt_id), {}),
            "note": "ComfyUI finished one keyframe-window segment.",
        }
