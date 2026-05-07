from __future__ import annotations

from importlib import import_module

_core = import_module("09_video.core.workflow_adapter")

collect_storyboard_images = _core.collect_storyboard_images
build_segment_plan = _core.build_segment_plan
build_ltx_prompt = _core.build_ltx_prompt
build_comfyui_workflow_payload = _core.build_comfyui_workflow_payload
