import shutil
from pathlib import Path

from backend.app.project_actions import import_source_text
from backend.agents.director_agent import next_step
from backend.app.node_store import list_nodes


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_import_source_and_generate_pipeline_nodes():
    project_id = "test_agent_pipeline"
    cleanup(project_id)
    import_source_text(project_id, "test title", "你站在衙门门口。县令冷笑一声。你终于明白，这身皂服不是荣耀。")
    for _ in range(5):
        next_step(project_id)
    assert list_nodes(project_id, "source_text")
    assert list_nodes(project_id, "script_block")
    assert list_nodes(project_id, "character_asset")
    assert list_nodes(project_id, "scene_asset")
    assert list_nodes(project_id, "shot")
    assert list_nodes(project_id, "storyboard_grid")
    cleanup(project_id)
