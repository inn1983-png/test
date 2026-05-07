from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Iterable

SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_silence_wav(path: str | Path, duration_seconds: float, sample_rate: int = SAMPLE_RATE) -> None:
    """Write a valid mono PCM silence wav for dry-run and pause segments."""
    ensure_parent(path)
    duration = max(float(duration_seconds), 0.05)
    frame_count = max(1, int(duration * sample_rate))
    silent_frame = (0).to_bytes(SAMPLE_WIDTH, byteorder="little", signed=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        chunk = silent_frame * min(frame_count, sample_rate)
        remaining = frame_count
        while remaining > 0:
            n = min(remaining, sample_rate)
            wf.writeframes(chunk[: n * SAMPLE_WIDTH])
            remaining -= n


def read_wav_duration(path: str | Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate() or SAMPLE_RATE
    return round(frames / rate, 3)


def concat_wavs(paths: Iterable[str | Path], output_path: str | Path) -> float:
    """Concatenate wav files. All files are converted only by assuming same format.

    The module writes dry-run audio in a consistent 24kHz mono format. For real
    IndexTTS output, the first generated file defines the output parameters; if a
    later file has a mismatched format this raises, so the user notices early.
    """
    paths = [Path(p) for p in paths]
    ensure_parent(output_path)
    if not paths:
        write_silence_wav(output_path, 0.5)
        return read_wav_duration(output_path)

    params = None
    total_frames = 0
    with wave.open(str(output_path), "wb") as out:
        for path in paths:
            with wave.open(str(path), "rb") as src:
                src_params = src.getparams()
                if params is None:
                    params = src_params
                    out.setparams(src_params)
                elif src_params[:4] != params[:4]:
                    raise RuntimeError(f"WAV format mismatch while concatenating: {path}")
                frames = src.readframes(src.getnframes())
                out.writeframes(frames)
                total_frames += src.getnframes()
    framerate = params.framerate if params else SAMPLE_RATE
    return round(total_frames / framerate, 3)


def estimate_speech_duration(text: str, speed_chars_per_second: float = 4.8) -> float:
    clean_len = len("".join(ch for ch in text.strip() if not ch.isspace()))
    if clean_len <= 0:
        return 0.35
    return round(max(0.6, clean_len / speed_chars_per_second), 3)
