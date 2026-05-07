from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONLEGACYWINDOWSSTDIO", "0")
    return env


class FFmpegClient:
    """Small deterministic FFmpeg wrapper for final packaging.

    10_final_assembly must not generate new video segments. This wrapper only
    performs concat/mux/subtitle-burn operations on already-produced files.
    """

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or os.getenv("AI_DRAMA_FFMPEG", "ffmpeg")
        self.available = shutil.which(self.binary) is not None

    def _run(self, cmd: list[str]) -> dict[str, Any]:
        if not self.available:
            return {"status": "unavailable", "cmd": cmd, "returncode": None, "stdout": "", "stderr": "ffmpeg not found"}
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace", env=_utf8_env())
        return {"status": "success" if proc.returncode == 0 else "failed", "cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    def concat_clips(self, clip_paths: list[Path], output_path: Path) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        list_path = output_path.parent / "10B_concat_list.txt"
        list_path.write_text("\n".join(f"file '{p.as_posix()}'" for p in clip_paths), encoding="utf-8")
        cmd = [self.binary, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output_path)]
        result = self._run(cmd)
        result.update({"operation": "concat_clips", "output_path": str(output_path), "concat_list_path": str(list_path)})
        return result

    def mux_video_audio(self, video_path: Path, audio_path: Path, output_path: Path) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.binary,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        result = self._run(cmd)
        result.update({"operation": "mux_video_audio", "output_path": str(output_path)})
        return result

    def burn_subtitles(self, video_path: Path, subtitle_path: Path, output_path: Path) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # FFmpeg subtitle filter is path-sensitive on Windows. Normalize slashes
        # and escape the most common filter-breaking characters.
        subtitle_filter_path = subtitle_path.as_posix().replace("'", "\\'").replace(":", "\\:")
        cmd = [
            self.binary,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"subtitles='{subtitle_filter_path}'",
            "-c:a",
            "copy",
            str(output_path),
        ]
        result = self._run(cmd)
        result.update({"operation": "burn_subtitles", "output_path": str(output_path), "subtitle_path": str(subtitle_path)})
        return result


def is_probably_valid_media(path: Path, min_bytes: int = 1024) -> bool:
    try:
        return path.exists() and path.stat().st_size >= min_bytes
    except OSError:
        return False
