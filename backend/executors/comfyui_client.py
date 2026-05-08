import json
import time
import urllib.request

from backend.app.settings_store import load_settings
from backend.app.workflow_store import load_workflow


def _json_request(url, payload=None, timeout=30):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def ping(project_id):
    settings = load_settings(project_id)
    url = settings.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
    try:
        return _json_request(url + "/system_stats", timeout=5)
    except Exception as exc:
        return {"error": str(exc)}


def submit_workflow(project_id, category, workflow_name, extra_inputs=None):
    settings = load_settings(project_id)
    base_url = settings.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
    workflow = load_workflow(project_id, category, workflow_name)
    if extra_inputs:
        workflow = patch_workflow_inputs(workflow, extra_inputs)
    return _json_request(base_url + "/prompt", {"prompt": workflow}, timeout=30)


def wait_for_prompt(project_id, prompt_id, timeout_seconds=None, poll_seconds=2):
    settings = load_settings(project_id)
    base_url = settings.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
    timeout_seconds = timeout_seconds or int(settings.get("task_timeout_seconds", 1800))
    start = time.time()
    while time.time() - start < timeout_seconds:
        history = _json_request(base_url + "/history/" + prompt_id, timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_seconds)
    raise TimeoutError("ComfyUI prompt timeout: " + prompt_id)


def run_workflow(project_id, category, workflow_name, extra_inputs=None):
    submitted = submit_workflow(project_id, category, workflow_name, extra_inputs)
    prompt_id = submitted.get("prompt_id")
    if not prompt_id:
        return submitted
    if not load_settings(project_id).get("wait_until_complete", True):
        return submitted
    return {"prompt_id": prompt_id, "history": wait_for_prompt(project_id, prompt_id)}


def patch_workflow_inputs(workflow, extra_inputs):
    patched = json.loads(json.dumps(workflow))
    for node_id, inputs in extra_inputs.items():
        if node_id in patched and "inputs" in patched[node_id]:
            patched[node_id]["inputs"].update(inputs)
    return patched


def _collect_files(obj, keys):
    files = []
    if isinstance(obj, dict):
        if "filename" in obj:
            files.append(obj["filename"])
        for key, value in obj.items():
            if key in keys and isinstance(value, list):
                files.extend(_collect_files(value, keys))
            elif isinstance(value, (dict, list)):
                files.extend(_collect_files(value, keys))
    elif isinstance(obj, list):
        for item in obj:
            files.extend(_collect_files(item, keys))
    return files


def extract_images_from_history(result):
    history = result.get("history", result) if isinstance(result, dict) else result
    return _collect_files(history, {"images"})


def extract_videos_from_history(result):
    history = result.get("history", result) if isinstance(result, dict) else result
    files = _collect_files(history, {"gifs", "videos", "animated"})
    return [f for f in files if str(f).lower().endswith((".mp4", ".webm", ".mov", ".gif"))] or files
