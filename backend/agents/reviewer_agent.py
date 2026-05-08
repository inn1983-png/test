from backend.app.node_store import load_node, update_node


def review_node(project_id, node_id):
    node = load_node(project_id, node_id)
    issues = []
    if node.get("type") == "shot" and not node.get("cap"):
        issues.append("missing cap")
    score = 100 if not issues else 60
    return update_node(project_id, node_id, {
        "review": {"score": score, "issues": issues},
        "status": "done" if score >= 80 else "needs_review",
    })
