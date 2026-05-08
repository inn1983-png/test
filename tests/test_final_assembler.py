import shutil
from pathlib import Path

from backend.executors.final_assembler import run


def cleanup(project_id):
    path = Path("projects") / project_id
    if path.exists():
        shutil.rmtree(path)


def test_final_assembler_no_video_clips_returns_needs_review_manifest():
    project_id = "test_final_assembler"
    cleanup(project_id)

    manifest = run(project_id)

    assert manifest["status"] == "needs_review"
    assert manifest["video_clips"] == []
    assert (Path("projects") / project_id / "final" / "final_manifest.json").exists()
    cleanup(project_id)
