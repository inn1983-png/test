import json
import time
import urllib.request
from urllib.error import URLError

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
    payload = {"prompt": workflow}
    return _json_request(base_url + "/prompt", payload, timeout=30)


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
    result = wait_for_prompt(project_id, prompt_id)
    return {"prompt_id": prompt_id, "history": result}


def patch_workflow_inputs(workflow, extra_inputs):
    # extra_inputs format:
    # {"node_id": {"input_name": value}}
    patched = json.loads(json.dumps(workflow))
    for node_id, inputs in extra_inputs.items():
        if node_id in patched and "inputs" in patched[node_id]:
            patched[node_id]["inputs"].update(inputs)
    return patched
