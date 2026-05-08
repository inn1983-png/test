# Development Log

## New-system-only cleanup

The repository has been rebuilt to keep only the Agent Canvas system.

Removed from `main`:

```text
00_common/
00_main_controller/
00_style_system/
01_novel_parser/
02_script_writer/
03_character_system/
04_scene_system/
05_prop_system/
06_storyboard/
07_storyboard_image/
08_audio/
09_video/
10_final_assembly/
configs/
web_ui/
pipeline.json
old tools and tests
```

Kept:

```text
backend/
frontend/
docs/
run.py
requirements.txt
README.md
```

Local-only items remain configurable in `projects/{project_id}/settings.json` and the Settings page.

## Current Agent Canvas status

The current audio path is IndexTTS. The repository provides an IndexTTS command adapter, while the actual inference script path, model path, and voice parameters remain local-only configuration through Settings or `projects/{project_id}/settings.json`.

ComfyUI workflow JSON is managed by the new workflow upload store and UI. Real workflow JSON files can be uploaded and categorized, and image/video execution uses configurable `workflow_mappings` rather than fixed placeholder node ids.

FFmpeg final assembly is implemented by the final executor. The `ffmpeg_path` value is still local-only configuration, so the repository must not hardcode a machine-specific FFmpeg path.

## Staged production and local checks

Dashboard now exposes staged production actions for script, assets, storyboard, image tasks, grid tasks, audio tasks, video tasks, and final assembly without breaking the existing `step` and `run` flows.

Storyboard now supports search, status filtering, and batch review / repair / rerun over the currently filtered shot set. Assets now supports Characters / Scenes / Props tabs, simple editing for `visual_lock`, `negative_prompt`, and `locked`, plus a lock-all action.

Settings now includes ComfyUI ping, FFmpeg version check, IndexTTS command preview, and workflow JSON validation. The IndexTTS checker reports whether `indextts_command` is configured and detects a local `index-tts/` directory when present, but it does not hardcode or execute a long generation command.

Preview now reads `projects/{project_id}/final/final_manifest.json` through the API and displays status, output, `ffmpeg_path`, clips, missing files, command, stdout, and stderr. When `final/final.mp4` exists, the API exposes it for optional browser preview.

Added focused pytest coverage for settings deep merge, source import reset, audio executor empty IndexTTS command, final assembler no-video manifest, task runner failure logging, and workflow JSON save/load.

## Local IndexTTS voices and Gemma LLM config

Settings now supports `indextts_root` and `indextts_voice_index`, with a backend voice-library reader for the root `index-tts/examples/voice_index.json`. The audio executor supports `{voice_file}` and `{indextts_root}` placeholders in addition to the existing text and output placeholders.

Narration uses `narrator_voice_id` and the demo project pins it to `voice_06` (`男中年-说书`). Character assets expose a per-character `voice_id` field in the Assets page so user-selected role voices can be stored independently of narration.

Settings also includes local `llama.cpp` / Gemma configuration fields using an OpenAI-compatible base URL. The LLM check reads local path configuration and probes `/v1/models`; the application does not pass Codex chat context to the local model.
