from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def safe_key(value: str) -> str:
    text = str(value or "").strip()
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text) or "asset"


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def asset_image_base() -> str:
    return os.getenv("AI_DRAMA_ASSET_IMAGE_BASE", "shared_assets").rstrip("/")


def output_image_path(output_dir: str | Path, category: str, filename_key: str) -> str:
    root = Path(output_dir) / "images" / category
    root.mkdir(parents=True, exist_ok=True)
    return _repo_relative(root / f"{safe_key(filename_key)}.png")


def reference_image_path(kind: str, key: str) -> str:
    base = asset_image_base()
    return f"{base}/{kind}/{safe_key(key)}.png"
