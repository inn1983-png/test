import json
import base64
from backend.app.project_store import ensure_project_dirs, utc_now

CATEGORIES = ["image", "video", "audio", "grid", "final", "utility"]


def workflows_root(project_id):
    root = ensure_project_dirs(project_id) / "workflows"
    for category in CATEGORIES:
        (root / category).mkdir(parents=True, exist_ok=True)
    return root


def workflow_path(project_id, category, name):
    if category not in CATEGORIES:
        raise ValueError("unknown workflow category")
    safe_name = name.replace("/", "_").replace("\\", "_")
    if not safe_name.endswith(".json"):
        safe_name += ".json"
    return workflows_root(project_id) / category / safe_name


def list_workflows(project_id):
    root = workflows_root(project_id)
    items = []
    for category in CATEGORIES:
        for path in sorted((root / category).glob("*.json")):
            items.append({
                "category": category,
                "name": path.name,
                "path": "workflows/" + category + "/" + path.name,
                "updated_at": utc_now()
            })
    return items


def save_workflow(project_id, category, name, content):
    data = content
    if isinstance(content, dict):
        data = json.dumps(content, ensure_ascii=False, indent=2)
    else:
        text = str(content)
        try:
            parsed = json.loads(text)
            data = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            try:
                parsed = json.loads(base64.b64decode(text).decode("utf-8"))
                data = json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception as exc:
                raise ValueError("workflow content must be JSON or base64 JSON") from exc
    path = workflow_path(project_id, category, name)
    path.write_text(data, encoding="utf-8")
    return {"category": category, "name": path.name, "path": "workflows/" + category + "/" + path.name}


def load_workflow(project_id, category, name):
    path = workflow_path(project_id, category, name)
    return json.loads(path.read_text(encoding="utf-8"))
