import shutil
from pathlib import Path

from backend.app.settings_store import load_settings, save_settings


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_settings_deep_merge_keeps_workflow_mapping_defaults_and_indextts_command():
    project_id = "test_settings_store"
    cleanup(project_id)
    save_settings(project_id, {
        "workflow_mappings": {
            "image": {
                "prompt_node": "42"
            }
        },
        "indextts_command": "python -m indextts.cli --text {text_file} --output {output_file}",
    })

    settings = load_settings(project_id)

    assert settings["indextts_command"].startswith("python -m indextts.cli")
    assert settings["narrator_voice_id"] == "voice_06"
    assert settings["workflow_mappings"]["image"]["prompt_node"] == "42"
    assert settings["workflow_mappings"]["image"]["prompt_input"] == "text"
    assert settings["workflow_mappings"]["video"]["image_input"] == "image"
    cleanup(project_id)
