from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT_DIR / "projects"
LEGACY_DIR = ROOT_DIR / "legacy"

COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_PROJECT_ID = "demo_project"
DEFAULT_GRID_MODE = "grid_4"
DEFAULT_VIDEO_SECONDS = 12
TASK_TIMEOUT_SECONDS = 1800
MAX_RETRY = 3
