from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def postprocess_audio(final_audio_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Optional postprocess hook.

    This module intentionally keeps postprocess non-destructive by default. When
    ffmpeg exists and AI_DRAMA_AUDIO_NORMALIZE=1, it writes final_audio_normalized.wav
    and lets downstream users choose it later. The key output final_audio.wav stays
    stable for pipeline dependency checks.
    """
    final_audio_path = Path(final_audio_path)
    output_dir = Path(output_dir)
    enabled = os.getenv("AI_DRAMA_AUDIO_NORMALIZE", "0").strip().lower() in {"1", "true", "yes", "on"}
    ffmpeg = shutil.which("ffmpeg")
    result: dict[str, Any] = {
        "enabled": enabled,
        "ffmpeg_available": bool(ffmpeg),
        "source_audio_path": str(final_audio_path),
        "normalized_audio_path": None,
        "status": "skipped",
        "notes": [],
    }
    if not enabled:
        result["notes"].append("AI_DRAMA_AUDIO_NORMALIZE is disabled; keep raw final_audio.wav.")
        return result
    if not ffmpeg:
        result["status"] = "needs_review"
        result["notes"].append("ffmpeg not found; cannot normalize audio.")
        return result
    normalized = output_dir / "final_audio_normalized.wav"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(final_audio_path),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        str(normalized),
    ]
    completed = subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if completed.returncode != 0 or not normalized.exists():
        result["status"] = "needs_review"
        result["notes"].append(f"ffmpeg loudnorm failed with return code {completed.returncode}.")
        return result
    result.update({"status": "success", "normalized_audio_path": str(normalized)})
    return result
