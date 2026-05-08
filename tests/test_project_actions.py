import shutil
from pathlib import Path

import pytest

from backend.app.node_store import list_nodes, save_node
from backend.app.project_actions import import_source_text, run_project_action


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_import_source_text_clears_old_generated_nodes():
    project_id = "test_project_actions"
    cleanup(project_id)
    save_node(project_id, {"id": "source_001", "type": "source_text", "status": "done", "content": "old"})
    save_node(project_id, {"id": "script_001", "type": "script_block", "status": "done", "content": "old script"})
    save_node(project_id, {"id": "shot_001", "type": "shot", "status": "done", "cap": "old shot"})

    import_source_text(project_id, "new", "new source")

    sources = list_nodes(project_id, "source_text")
    assert len(sources) == 1
    assert sources[0]["content"] == "new source"
    assert list_nodes(project_id, "script_block") == []
    assert list_nodes(project_id, "shot") == []
    cleanup(project_id)


def test_generate_script_returns_clear_error_without_source_text():
    project_id = "test_project_actions_missing_source"
    cleanup(project_id)
    with pytest.raises(ValueError, match="source_text not found"):
        run_project_action(project_id, "generate-script")
    cleanup(project_id)
