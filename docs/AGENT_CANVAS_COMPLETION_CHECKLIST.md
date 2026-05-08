# Agent Canvas Completion Checklist

## Done

- Default entry: `run.py`
- Backend runtime: `backend/app`
- Agents: director, writer, asset, storyboard, reviewer, repair
- Executors: image, grid, audio, video, final
- ComfyUI adapter: `backend/executors/comfyui_client.py`
- Project data: `projects/{project_id}`
- Canvas data: `canvas.json`
- Node data: `nodes/*.json`
- Task queue: pending, running, done, failed, cancelled, logs
- Settings file: `settings.json`
- Workflow upload store: `workflows/{category}`
- Frontend workspace: `frontend/src/App.tsx`
- Frontend styles: `frontend/src/style.css`

## UI Done

- Dashboard
- Script
- Assets
- Storyboard
- Tasks
- Preview
- Settings
- Node Detail editor
- Node rerun
- Node review
- Node repair
- Node lock
- Task retry
- Task cancel
- Runtime settings form
- ComfyUI workflow JSON upload form
- Workflow category selector

## Workflow Categories

- image
- video
- audio
- grid
- final
- utility

## Reserved Local Settings

These are not hard-coded and must be set locally:

- ComfyUI URL
- ComfyUI workflow JSON files
- ComfyUI workflow node ids
- CosyVoice2 command and model path
- FFmpeg path
- Real generated media output paths

## Local Test Notes

Upload real ComfyUI workflow JSON files from the Settings page. Then set local paths in `projects/{project_id}/settings.json` or through the UI.

If an uploaded workflow uses different node ids, adjust the executor workflow mapping such as `PROMPT_NODE`, `NEGATIVE_NODE`, and `IMAGE_NODE`.
