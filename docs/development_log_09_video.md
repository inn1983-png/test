# 09_video 开发记录补充

本文件记录 09_video 本轮真实模块化搭建结果，作为 docs/development_log.md 的 09 视频阶段补充记录。

---

# 09 视频生成系统

正式入口：

```text
09_video/run_staged.py
```

阶段：

```text
09A audio_image_segment_plan
09B ltx23_comfyui_execution
09C breakpoint_resume_scan
09D final_merge_and_manifest_check
```

09 输入：

```text
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
08_audio/audio_timeline.json
```

09 输出：

```text
09_video/video_manifest.json
09_video/video_meta.json
09_video/video_plan.json
09_video/resume_manifest.json
09_video/merge_result.json
09_video/final_video.mp4
09_video/clips/clip_0001.mp4 ...
```

09 已按用户本地验证可运行的 LTX2.3 ComfyUI 工作流思路搭建：

```text
输入为 07_storyboard_image 的分镜图片文件夹 / image_manifest。
输入为 08_audio 的整章完整音频 final_audio.wav。
按 10 秒或 12 秒自动切割音频分段。
自动循环读取分镜图片并生成视频段。
支持断点续跑：已有 clip 默认跳过。
支持最终自动合并：默认尝试 ffmpeg concat，失败时写入合并占位以保证 manifest 可检查。
```

09 是 VIDEO_PHASE，不是 LLM_TEXT_PHASE：

```text
进入 09 前释放图片/音频资源。
09 完成后释放 LTX/video 资源。
09 不调用 LLM，不使用 JSON repair。
09 失败时只建议重跑 failed_video_segments，不回滚 06/07/08。
```

关键文件：

```text
09_video/run_staged.py
09_video/core/comfyui_client.py
09_video/core/workflow_adapter.py
09_video/workflow_adapter.py
09_video/core/quality_checker.py
09_video/core/schema_validator.py
09_video/core/stage_runner.py
09_video/README.md
configs/module_contracts.json
```

核心环境变量：

```text
AI_DRAMA_VIDEO_EXECUTION_MODE=dry_run|execute
AI_DRAMA_VIDEO_SEGMENT_SECONDS=10|12
AI_DRAMA_VIDEO_FPS=24
AI_DRAMA_VIDEO_WIDTH=1280
AI_DRAMA_VIDEO_HEIGHT=720
AI_DRAMA_VIDEO_COMFYUI_WORKFLOW=workflow_api.json
AI_DRAMA_VIDEO_FORCE_RERUN=0|1
AI_DRAMA_VIDEO_AUTO_MERGE=1|0
```

ComfyUI workflow 适配规则：

```text
09 不硬编码自制节点名，避免本地节点版本变化导致失效。
09 通过 AI_DRAMA_VIDEO_NODE_* 环境变量将 prompt、image_path、audio_path、project_name、base_path、current_chunk、duration、fps、width、height、frame_count、overlap_frames、output_prefix 等语义字段注入到本地 LTX2.3 API workflow。
桌面 workflow 需要先在 ComfyUI 中导出 API workflow，再配置对应 node_id:input_key。
```
