# Agent Canvas Completion Checklist

This repository keeps only the new Agent Canvas system. Local machine paths must not be hardcoded in code or docs; configure them through the Settings UI or `projects/{project_id}/settings.json`.

## Completed In Repository

- [x] Default entry: `run.py`
- [x] Backend runtime
- [x] Project / Canvas / Node / Task stores
- [x] Settings store
- [x] Workflow upload store
- [x] HTTP API
- [x] Source import API and UI
- [x] Workflow node mapping settings and UI
- [x] Director / Writer / Asset / Storyboard / Reviewer / Repair agents
- [x] Image / Grid / Audio / Video / Final executors
- [x] ComfyUI client adapter
- [x] ComfyUI history output extraction
- [x] Image executor uses configurable workflow mapping
- [x] Video executor uses configurable workflow mapping
- [x] Real `grid_4` / `grid_6` / `grid_9` image builder
- [x] IndexTTS command adapter
- [x] FFmpeg final assembly executor
- [x] Task runner logs, traceback and duration
- [x] React frontend workspace
- [x] Dashboard / Script / Assets / Storyboard / Tasks / Preview / Settings pages
- [x] Node Detail editor
- [x] Workflow JSON upload form
- [x] Task log viewer in UI
- [x] Basic pytest tests

## Workflow Mapping Configuration

ComfyUI workflow node ids and input names are local configuration. Use Settings or `projects/{project_id}/settings.json` to set:

```text
workflow_mappings.image.prompt_node
workflow_mappings.image.prompt_input
workflow_mappings.image.negative_node
workflow_mappings.image.negative_input
workflow_mappings.video.prompt_node
workflow_mappings.video.prompt_input
workflow_mappings.video.image_node
workflow_mappings.video.image_input
```

## Completed Repository Enhancements

- [x] Dashboard staged action buttons and matching APIs
- [x] Storyboard search, status filters, and batch operations
- [x] Assets tabs and simple form editing for asset fields
- [x] Settings checks for ComfyUI, FFmpeg, IndexTTS, and workflow JSON
- [x] Settings support for root IndexTTS voice library discovery
- [x] Fixed narrator voice setting plus per-character voice selection
- [x] Settings support for local llama.cpp / Gemma LLM configuration
- [x] Preview page final manifest display
- [x] Expanded tests for settings, task runner, audio, final assembly, project actions, and workflow store
- [x] README update after the remaining enhancements are complete

## Local-only Completion

- [ ] Set ComfyUI URL
- [ ] Upload real ComfyUI workflow JSON files
- [ ] Confirm ComfyUI workflow node ids and input names
- [ ] Set IndexTTS inference script path, model path, voice parameters, and `indextts_command`
- [ ] Set FFmpeg path
- [ ] Run real image generation test
- [ ] Run real audio generation test
- [ ] Run real video generation test
- [ ] Run real final assembly test

## Local Configuration Rule

```text
Do not hardcode local paths.
Do not hardcode ComfyUI workflow node ids.
Do not hardcode IndexTTS model paths.
Do not hardcode FFmpeg paths.
Use Settings UI or projects/{project_id}/settings.json.
```
