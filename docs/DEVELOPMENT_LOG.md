# Development Log

## Agent Canvas full refactor notes

This repository has been switched from the old module pipeline entry to the Agent Canvas workspace entry.

Default runtime:

```bash
python run.py init --project demo_project
python run.py run --project demo_project
python run.py serve --host 127.0.0.1 --port 7860
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## Local path settings reserved for user machine

The following values are intentionally not hard-coded because they depend on the local machine:

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "image_workflow": "workflows/image/storyboard_image.json",
  "video_workflow": "workflows/video/ltx23_grid_video.json",
  "cosyvoice2_command": "",
  "ffmpeg_path": "ffmpeg"
}
```

Edit them in:

```text
projects/{project_id}/settings.json
```

or in the frontend Settings page.

---

## ComfyUI workflow upload rule

ComfyUI workflow JSON supports online upload from the frontend Settings page.

Workflow files are stored by function category:

```text
projects/{project_id}/workflows/image/
projects/{project_id}/workflows/video/
projects/{project_id}/workflows/audio/
projects/{project_id}/workflows/grid/
projects/{project_id}/workflows/final/
projects/{project_id}/workflows/utility/
```

Recommended categories:

```text
image   = storyboard image generation, character image, scene image, prop image
video   = LTX2.3 / image-to-video / grid-to-video
audio   = CosyVoice2 / voice / subtitle workflow
grid    = grid_4 / grid_6 / grid_9 storyboard board builder
final   = final assembly workflow
utility = helper workflow, prompt reverse, metadata extraction
```

The upload endpoint accepts raw JSON string, JSON object, or base64 encoded JSON:

```text
POST /api/projects/{project_id}/workflows
```

Body:

```json
{
  "category": "video",
  "name": "ltx23_grid_video.json",
  "content": "{...ComfyUI workflow JSON...}"
}
```

---

## Current integration status

Completed in repository structure:

```text
Agent Canvas runtime
Project store
Canvas store
Node store
Task queue
Settings store
Workflow category store
Director / Writer / Asset / Storyboard / Reviewer / Repair agents
Image / Grid / Audio / Video / Final executors
Task runner
React workspace UI
Workflow upload UI
Node editor / rerun / review / repair / lock actions
Task retry / cancel / log actions
```

Still local-machine dependent:

```text
Exact ComfyUI workflow node ids
CosyVoice2 executable and model path
FFmpeg binary path
Actual generated media files
```

These are exposed through settings and workflow upload instead of hard-coded.
