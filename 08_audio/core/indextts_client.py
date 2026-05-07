from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

from importlib import import_module

wav_utils = import_module("08_audio.core.wav_utils")

ROOT_DIR = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: str) -> Path:
    value = os.getenv(name, default).strip()
    path = Path(value)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


def get_execution_mode() -> str:
    return os.getenv("AI_DRAMA_AUDIO_EXECUTION_MODE", os.getenv("AI_DRAMA_TTS_EXECUTION_MODE", "dry_run")).strip().lower() or "dry_run"


def get_index_tts_root() -> Path:
    return _env_path("AI_DRAMA_INDEX_TTS_ROOT", "index-tts")


def get_default_voice_prompt() -> str:
    return os.getenv("AI_DRAMA_TTS_DEFAULT_VOICE", "examples/voice_07.wav").strip()


def get_default_emo_audio() -> str:
    return os.getenv("AI_DRAMA_TTS_DEFAULT_EMO_AUDIO", "").strip()


def get_emo_alpha() -> float:
    try:
        return float(os.getenv("AI_DRAMA_TTS_EMO_ALPHA", "0.6"))
    except ValueError:
        return 0.6


def use_fp16() -> bool:
    return os.getenv("AI_DRAMA_TTS_FP16", "1").strip().lower() in {"1", "true", "yes", "on"}


def use_deepspeed() -> bool:
    return os.getenv("AI_DRAMA_TTS_DEEPSPEED", "0").strip().lower() in {"1", "true", "yes", "on"}


def use_cuda_kernel() -> bool:
    return os.getenv("AI_DRAMA_TTS_CUDA_KERNEL", "0").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_inside(root: Path, value: str | None) -> Path:
    raw = (value or get_default_voice_prompt()).strip()
    p = Path(raw)
    if p.is_absolute():
        return p
    return root / p


def diagnose_environment() -> dict[str, Any]:
    root = get_index_tts_root()
    checkpoints = root / "checkpoints"
    cfg = checkpoints / "config.yaml"
    voice = _resolve_inside(root, get_default_voice_prompt())
    return {
        "index_tts_root": str(root),
        "root_exists": root.exists(),
        "checkpoints_dir": str(checkpoints),
        "checkpoints_exists": checkpoints.exists(),
        "config_yaml": str(cfg),
        "config_yaml_exists": cfg.exists(),
        "default_voice_prompt": str(voice),
        "default_voice_prompt_exists": voice.exists(),
        "uv_available": shutil.which("uv") is not None,
        "execution_mode": get_execution_mode(),
        "fp16": use_fp16(),
        "deepspeed": use_deepspeed(),
        "cuda_kernel": use_cuda_kernel(),
    }


def build_segment_plan(queue: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    segment_dir = output_dir / "segments"
    segment_dir.mkdir(parents=True, exist_ok=True)
    env = diagnose_environment()
    segments: list[dict[str, Any]] = []
    for index, line in enumerate(queue, start=1):
        segment_id = f"audio_seg_{index:04d}"
        text = str(line.get("text") or "").strip()
        line_type = str(line.get("line_type") or "dialogue")
        if line_type.upper() in {"S", "SILENCE", "留白"}:
            duration = float(line.get("pause_after_seconds") or 1.0)
            pause_after = 0.0
        else:
            duration = wav_utils.estimate_speech_duration(text)
            pause_after = float(line.get("pause_after_seconds") or 0.15)
        output_path = segment_dir / f"{segment_id}.wav"
        emotion_mapping = line.get("emotion_mapping", {}) if isinstance(line.get("emotion_mapping"), dict) else {}
        segments.append(
            {
                "segment_id": segment_id,
                "audio_line_id": line.get("audio_line_id"),
                "speaker": line.get("speaker") or "Narrator",
                "line_type": line_type,
                "text": text,
                "emotion": line.get("emotion") or "calm",
                "emotion_mapping": emotion_mapping,
                "voice_id": line.get("voice_id"),
                "spk_audio_prompt": line.get("spk_audio_prompt") or get_default_voice_prompt(),
                "voice_bind_type": line.get("voice_bind_type"),
                "estimated_duration_seconds": duration,
                "pause_after_seconds": pause_after,
                "output_path": str(output_path),
                "status": "planned",
            }
        )
    return {
        "stage": "08B_tts_segment_plan",
        "status": "success" if segments else "needs_review",
        "execution_mode": get_execution_mode(),
        "environment": env,
        "segments": segments,
        "notes": [
            "08B 为每条对白/OS/旁白建立独立音频段，后续可按失败段局部重跑。",
            "本项目只引用本地根目录 index-tts，不把 IndexTTS 权重复制进仓库。",
        ],
    }


def _script_for_index_tts(segment: dict[str, Any], output_path: Path, root: Path) -> str:
    text = json.dumps(segment.get("text") or "", ensure_ascii=False)
    voice = json.dumps(str(_resolve_inside(root, str(segment.get("spk_audio_prompt") or get_default_voice_prompt()))), ensure_ascii=False)
    out = json.dumps(str(output_path), ensure_ascii=False)
    root_json = json.dumps(str(root), ensure_ascii=False)
    emo_audio = get_default_emo_audio()
    emo_audio_arg = "None"
    if emo_audio:
        emo_audio_arg = json.dumps(str(_resolve_inside(root, emo_audio)), ensure_ascii=False)
    mapping = segment.get("emotion_mapping", {}) if isinstance(segment.get("emotion_mapping"), dict) else {}
    emo_text = json.dumps(str(mapping.get("emo_text") or segment.get("emotion") or "calm"), ensure_ascii=False)
    emo_alpha = float(mapping.get("emo_alpha") if mapping.get("emo_alpha") is not None else get_emo_alpha())
    return textwrap.dedent(
        f"""
        import os
        import sys
        sys.path.insert(0, {root_json})
        os.chdir({root_json})
        from indextts.infer_v2 import IndexTTS2
        tts = IndexTTS2(
            cfg_path="checkpoints/config.yaml",
            model_dir="checkpoints",
            use_fp16={use_fp16()!r},
            use_cuda_kernel={use_cuda_kernel()!r},
            use_deepspeed={use_deepspeed()!r},
        )
        tts.infer(
            spk_audio_prompt={voice},
            text={text},
            output_path={out},
            emo_audio_prompt={emo_audio_arg},
            emo_alpha={emo_alpha!r},
            use_emo_text=True,
            emo_text={emo_text},
            use_random=False,
            verbose=True,
        )
        """
    ).strip()


def synthesize_segments(plan: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    mode = get_execution_mode()
    root = get_index_tts_root()
    results: list[dict[str, Any]] = []
    for segment in plan.get("segments", []) or []:
        if not isinstance(segment, dict):
            continue
        out_path = Path(segment["output_path"])
        try:
            if str(segment.get("line_type") or "").upper() in {"S", "SILENCE", "留白"}:
                wav_utils.write_silence_wav(out_path, float(segment.get("estimated_duration_seconds") or 1.0))
            elif mode == "execute":
                env = diagnose_environment()
                voice_path = _resolve_inside(root, str(segment.get("spk_audio_prompt") or get_default_voice_prompt()))
                missing = [key for key in ("root_exists", "checkpoints_exists", "config_yaml_exists", "uv_available") if not env.get(key)]
                if not voice_path.exists():
                    missing.append(f"voice_prompt_missing:{voice_path}")
                if missing:
                    raise RuntimeError(f"IndexTTS environment is not ready: missing {missing}")
                code = _script_for_index_tts(segment, out_path, root)
                temp_script = Path(output_dir) / "intermediate" / f"run_{segment['segment_id']}.py"
                temp_script.parent.mkdir(parents=True, exist_ok=True)
                temp_script.write_text(code, encoding="utf-8")
                completed = subprocess.run(["uv", "run", str(temp_script)], cwd=str(root), check=False)
                if completed.returncode != 0:
                    raise RuntimeError(f"IndexTTS uv run failed with return code {completed.returncode}")
            else:
                wav_utils.write_silence_wav(out_path, float(segment.get("estimated_duration_seconds") or 0.8))

            pause = float(segment.get("pause_after_seconds") or 0)
            pause_path = None
            if pause > 0:
                pause_path = out_path.with_name(out_path.stem + "__pause.wav")
                wav_utils.write_silence_wav(pause_path, pause)

            duration = wav_utils.read_wav_duration(out_path)
            results.append({**segment, "status": "success", "actual_duration_seconds": duration, "pause_path": str(pause_path) if pause_path else None, "execution_mode": mode})
        except Exception as exc:  # noqa: BLE001
            results.append({**segment, "status": "failed", "error": str(exc), "execution_mode": mode})

    failed = [item for item in results if item.get("status") != "success"]
    return {
        "stage": "08C_tts_execution",
        "status": "needs_retry" if failed else "success",
        "execution_mode": mode,
        "segments": results,
        "failed_segments": failed,
        "execution_summary": {
            "total": len(results),
            "success": len(results) - len(failed),
            "failed": len(failed),
        },
    }
