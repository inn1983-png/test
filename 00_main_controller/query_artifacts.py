from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from importlib import import_module

artifact_registry = import_module("00_common.artifact_registry")
artifact_db = import_module("00_common.artifact_db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query runtime artifacts.")
    parser.add_argument("--run-dir", required=True, help="Runtime directory under workspace.")
    parser.add_argument("--module", default=None, help="Filter by module name.")
    parser.add_argument("--type", default=None, help="Filter by artifact type.")
    parser.add_argument("--name", default=None, help="Filter by artifact name.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--keys", action="store_true", help="Show manifest key outputs only.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT_DIR / run_dir

    if not run_dir.exists():
        print(f"Run dir not found: {run_dir}")
        return 1

    manifest = artifact_registry.load_manifest(run_dir)

    print("Run directory:", run_dir)
    print("Artifact summary:", manifest.get("artifact_summary", {}))

    if args.keys:
        print("\nKey outputs:")
        key_outputs = manifest.get("key_outputs", {})
        for module_name, items in key_outputs.items():
            print(f"\n[{module_name}]")
            for name, item in items.items():
                print(f"- {name}: {item.get('path')} ({item.get('type')})")
        return 0

    print("\nArtifacts:")
    rows = artifact_db.find_artifacts(
        run_dir=run_dir,
        module_name=args.module,
        artifact_type=args.type,
        artifact_name=args.name,
        limit=args.limit,
    )
    for row in rows:
        print(f"- #{row['id']} [{row['module']}] {row['name']} | {row['type']} | {row['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
