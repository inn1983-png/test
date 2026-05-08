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
