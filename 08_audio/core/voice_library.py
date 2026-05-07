from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_VOICE_MAP = {
    "schema_version": "1.0",
    "default_voice_id": "narrator_default",
    "narrator": {
        "voice_id": "narrator_default",
        "spk_audio_prompt": "examples/voice_07.wav",
        "description": "默认旁白音色。",
    },
    "roles": {},
    "fallbacks": {
        "male": "narrator_default",
        "female": "narrator_default",
        "unknown": "narrator_default",
    },
}


def _candidate_paths(output_dir: str | Path | None = None) -> list[Path]:
    paths: list[Path] = []
    env_path = os.getenv("AI_DRAMA_VOICE_MAP", "").strip()
    if env_path:
        p = Path(env_path)
        paths.append(p if p.is_absolute() else ROOT_DIR / p)

    shared_assets = os.getenv("AI_DRAMA_SHARED_ASSETS_DIR", "").strip()
    if shared_assets:
        paths.append(Path(shared_assets) / "voice_library" / "voices.json")
        paths.append(Path(shared_assets) / "voice_library" / "voice_map.json")

    paths.append(ROOT_DIR / "shared_assets" / "voice_library" / "voices.json")
    paths.append(ROOT_DIR / "shared_assets" / "voice_library" / "voice_map.json")
    return paths


def load_voice_map(output_dir: str | Path | None = None) -> dict[str, Any]:
    for path in _candidate_paths(output_dir):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {**DEFAULT_VOICE_MAP, "load_error": str(exc), "source_path": str(path)}
        if isinstance(data, dict):
            return {**DEFAULT_VOICE_MAP, **data, "source_path": str(path)}
    return {**DEFAULT_VOICE_MAP, "source_path": None, "note": "voice map not found; using narrator fallback"}


def _voice_entry_by_id(voice_map: dict[str, Any], voice_id: str | None) -> dict[str, Any] | None:
    if not voice_id:
        return None
    if voice_map.get("narrator", {}).get("voice_id") == voice_id:
        return voice_map.get("narrator")
    roles = voice_map.get("roles", {})
    if isinstance(roles, dict):
        for value in roles.values():
            if isinstance(value, dict) and value.get("voice_id") == voice_id:
                return value
    voices = voice_map.get("voices", {})
    if isinstance(voices, dict):
        value = voices.get(voice_id)
        if isinstance(value, dict):
            return {"voice_id": voice_id, **value}
    return None


def resolve_voice_for_line(line: dict[str, Any], voice_map: dict[str, Any]) -> dict[str, Any]:
    speaker = str(line.get("speaker") or "Narrator").strip() or "Narrator"
    line_type = str(line.get("line_type") or "").upper()

    if speaker.upper() in {"N", "OS", "NARRATOR", "旁白"} or line_type in {"N", "NARRATION", "旁白"}:
        entry = voice_map.get("narrator") if isinstance(voice_map.get("narrator"), dict) else None
        if entry:
            return {"bind_type": "narrator", "speaker": speaker, **entry}

    roles = voice_map.get("roles", {})
    if isinstance(roles, dict):
        role_entry = roles.get(speaker)
        if isinstance(role_entry, str):
            found = _voice_entry_by_id(voice_map, role_entry)
            if found:
                return {"bind_type": "role", "speaker": speaker, **found}
        if isinstance(role_entry, dict):
            return {"bind_type": "role", "speaker": speaker, **role_entry}

    fallback_id = None
    fallbacks = voice_map.get("fallbacks", {})
    if isinstance(fallbacks, dict):
        fallback_id = fallbacks.get("unknown") or voice_map.get("default_voice_id")
    found = _voice_entry_by_id(voice_map, fallback_id)
    if found:
        return {"bind_type": "fallback", "speaker": speaker, **found}

    narrator = voice_map.get("narrator", {}) if isinstance(voice_map.get("narrator"), dict) else {}
    return {"bind_type": "fallback", "speaker": speaker, **narrator}


def bind_voices(queue: list[dict[str, Any]], output_dir: str | Path | None = None) -> dict[str, Any]:
    voice_map = load_voice_map(output_dir)
    bound_lines: list[dict[str, Any]] = []
    for line in queue:
        if not isinstance(line, dict):
            continue
        binding = resolve_voice_for_line(line, voice_map)
        bound_lines.append(
            {
                **line,
                "voice_id": binding.get("voice_id"),
                "spk_audio_prompt": binding.get("spk_audio_prompt"),
                "voice_bind_type": binding.get("bind_type"),
                "voice_description": binding.get("description"),
            }
        )
    return {
        "voice_map": voice_map,
        "voice_queue": bound_lines,
        "voice_binding_summary": {
            "line_count": len(bound_lines),
            "voice_ids": sorted({str(line.get("voice_id")) for line in bound_lines if line.get("voice_id")}),
            "fallback_count": sum(1 for line in bound_lines if line.get("voice_bind_type") == "fallback"),
        },
    }
