from backend.executors.assembly_manifest import build


def run(project_id, node_id="final"):
    return build(project_id)
