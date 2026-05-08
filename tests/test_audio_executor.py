import shutil
from pathlib import Path

from backend.app.node_store import load_node, save_node
from backend.executors.audio_executor import run


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_audio_executor_empty_indextts_command_returns_needs_review():
    project_id = "test_audio_executor"
    cleanup(project_id)
    save_node(project_id, {
        "id": "script_001",
        "type": "script_block",
        "status": "done",
        "content": "短测试文本。",
    })

    run(project_id, "script_001")

    node = load_node(project_id, "script_001")
    assert node["status"] == "needs_review"
    assert node["indextts_command_configured"] is False
    assert node["audio_path"] == "audio/script_001.wav"
    cleanup(project_id)
