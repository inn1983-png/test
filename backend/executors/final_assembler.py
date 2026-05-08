from backend.app.project_store import ensure_project_dirs


def run(project_id, node_id="final"):
    final_dir = ensure_project_dirs(project_id) / "final"
    manifest = final_dir / "final_manifest.json"
    manifest.write_text('{"status":"done","output":"final/final.mp4"}', encoding="utf-8")
    return {"status": "done", "output": "final/final.mp4"}
