from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

from backend.app.node_store import load_node, update_node
from backend.app.project_store import ensure_project_dirs


def _layout(mode, count):
    if mode == "grid_9":
        return 3, 3
    if mode == "grid_6":
        return 3, 2
    return 2, 2


def _resolve_image(project_dir, image_path):
    if not image_path:
        return None
    candidate = Path(image_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for base in [project_dir, project_dir / "images", project_dir / "grids"]:
        path = base / image_path
        if path.exists():
            return path
        path = base / Path(image_path).name
        if path.exists():
            return path
    return None


def _fit_image(path, size):
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def run(project_id, node_id):
    project_dir = ensure_project_dirs(project_id)
    node = load_node(project_id, node_id)
    shot_ids = node.get("shot_ids", [])
    if not shot_ids:
        return update_node(project_id, node_id, {"status": "needs_review", "error": "grid has no shot_ids"})

    image_paths = []
    missing = []
    for shot_id in shot_ids:
        shot = load_node(project_id, shot_id)
        resolved = _resolve_image(project_dir, shot.get("image_path") or shot.get("comfyui_output"))
        if resolved:
            image_paths.append(resolved)
        else:
            missing.append(shot_id)

    if missing:
        return update_node(project_id, node_id, {
            "status": "needs_review",
            "error": "missing shot images: " + ", ".join(missing),
            "missing_shot_ids": missing,
        })

    cols, rows = _layout(node.get("grid_mode", "grid_4"), len(image_paths))
    cell_size = int(node.get("cell_size", 768))
    margin = int(node.get("margin", 8))
    width = cols * cell_size + (cols + 1) * margin
    height = rows * cell_size + (rows + 1) * margin
    canvas = Image.new("RGB", (width, height), (18, 19, 24))
    draw = ImageDraw.Draw(canvas)

    for index, path in enumerate(image_paths):
        row = index // cols
        col = index % cols
        if row >= rows:
            break
        x = margin + col * (cell_size + margin)
        y = margin + row * (cell_size + margin)
        canvas.paste(_fit_image(path, (cell_size, cell_size)), (x, y))
        draw.text((x + 12, y + 12), str(index + 1), fill=(255, 255, 255))

    out_rel = "grids/" + node_id + ".png"
    out_path = project_dir / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return update_node(project_id, node_id, {
        "status": "done",
        "grid_path": out_rel,
        "shot_count": len(image_paths),
        "grid_layout": {"cols": cols, "rows": rows, "cell_size": cell_size},
    })
