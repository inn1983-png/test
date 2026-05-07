from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def main() -> int:
    host = os.getenv("AI_DRAMA_WEB_UI_HOST", "127.0.0.1")
    port = os.getenv("AI_DRAMA_WEB_UI_PORT", "1144")
    cmd = [sys.executable, str(ROOT_DIR / "web_ui" / "server.py"), "--host", host, "--port", port]
    print(f"启动 AI 短剧工厂 Web UI: http://{host}:{port}")
    return subprocess.call(cmd, cwd=str(ROOT_DIR))


if __name__ == "__main__":
    raise SystemExit(main())
