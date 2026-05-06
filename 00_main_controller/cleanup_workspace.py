from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean project/chapter runtime data safely.")
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project", help="Delete one short project runtime directory.")
    project.add_argument("--project-id", required=True)
    project.add_argument("--yes", action="store_true", help="Confirm deletion.")

    chapter = sub.add_parser("chapter", help="Delete one long-novel chapter runtime directory, keeping shared assets.")
    chapter.add_argument("--book-id", required=True)
    chapter.add_argument("--chapter-id", required=True)
    chapter.add_argument("--yes", action="store_true", help="Confirm deletion.")

    book = sub.add_parser("book", help="Delete a whole long-novel book, including shared assets.")
    book.add_argument("--book-id", required=True)
    book.add_argument("--yes", action="store_true", help="Confirm deletion.")

    return parser


def ensure_under_workspace(path: Path) -> None:
    workspace = (ROOT_DIR / "workspace").resolve()
    target = path.resolve()
    if workspace not in target.parents and target != workspace:
        raise ValueError(f"Refuse to delete outside workspace: {target}")


def delete_dir(path: Path, confirmed: bool) -> int:
    ensure_under_workspace(path)

    if not path.exists():
        print(f"[SKIP] Not found: {path}")
        return 0

    if not confirmed:
        print("Refusing to delete without --yes.")
        print(f"Target: {path}")
        return 2

    shutil.rmtree(path)
    print(f"[DELETED] {path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "project":
        target = ROOT_DIR / "workspace" / "projects" / args.project_id
        return delete_dir(target, args.yes)

    if args.command == "chapter":
        target = ROOT_DIR / "workspace" / "books" / args.book_id / "chapters" / args.chapter_id
        return delete_dir(target, args.yes)

    if args.command == "book":
        target = ROOT_DIR / "workspace" / "books" / args.book_id
        return delete_dir(target, args.yes)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
