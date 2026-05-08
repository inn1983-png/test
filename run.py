"""Agent Canvas local runtime entry.

This replaces the old module-pipeline-first entry with a lightweight local
workspace runner. It does not require FastAPI; it uses the Python standard
library so the refactor can start without heavy dependencies.
"""
from __future__ import annotations

import argparse

from backend.app.main import run_cli, run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Short Drama Agent Canvas")
    parser.add_argument("command", nargs="?", default="init", choices=["init", "step", "run", "serve"], help="runtime command")
    parser.add_argument("--project", default="demo_project", help="project id")
    parser.add_argument("--host", default="127.0.0.1", help="server host")
    parser.add_argument("--port", type=int, default=7860, help="server port")
    args = parser.parse_args()

    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return

    run_cli(command=args.command, project_id=args.project)


if __name__ == "__main__":
    main()
