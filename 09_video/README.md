# 09 视频生成系统

## 模块定位

09_video 是真实视频执行模块，负责读取 07_storyboard_image 的分镜图片与 08_audio 的整章完整音频 `final_audio.wav`，按 10 秒或 12 秒切割音频分段，自动循环绑定分镜图片，调用本地 LTX2.3 ComfyUI 工作流生成视频段，并支持断点续跑与最终自动合并。

它是 VIDEO_PHASE，不是 LLM_TEXT_PHASE：

```text
07_storyboard_image + 08_audio → 09_video → 10_final_assembly
```

09 不负责重新写剧本、不负责补剧情、不负责重做分镜图、不负责重新配音。

---

## 正式入口

```bash
python 09_video/run_staged.py
```

在总控中运行：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 09_video
```

---

## 阶段

```text
09A audio_image_segment_plan
09B ltx23_comfyui_execution
09C breakpoint_resume_scan
09D final_merge_and_manifest_check
```

### 09A：音频 + 分镜图分段规划

读取：

```text
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
08_audio/audio_timeline.json
```

生成：

```text
09_video/video_plan.json
09_video/intermediate/09A_video_segment_plan.json
```

核心逻辑：

```text
按 final_audio.wav / audio_timeline 的真实时长切片。
默认每段 10 秒。
可通过 AI_DRAMA_VIDEO_SEGMENT_SECONDS=12 改为 12 秒。
分镜图按 07 的 sequence_index 顺序循环绑定。
如果音频段数多于图片数，按图片顺序取模复用。
```

### 09B：LTX2.3 ComfyUI 执行

生成：

```text
09_video/clips/clip_0001.mp4
09_video/clips/clip_0002.mp4
09_video/intermediate/09B_ltx23_execution.json
```

默认 `dry_run` 会生成可被下游检查的占位/静帧视频段。`execute` 模式会调用本地 ComfyUI `/prompt`。

### 09C：断点续跑扫描

生成：

```text
09_video/resume_manifest.json
09_video/intermediate/09C_resume_scan.json
```

核心逻辑：

```text
已存在 clip_XXXX.mp4 时默认跳过。
缺失片段写入 missing_segments。
失败只建议重跑 failed_video_segments，不回滚 06/07/08。
需要重新抽卡时设置 AI_DRAMA_VIDEO_FORCE_RERUN=1。
```

### 09D：最终合并

生成：

```text
09_video/merge_result.json
09_video/final_video.mp4
09_video/video_manifest.json
09_video/video_meta.json
```

默认尝试使用 ffmpeg concat 合并所有已完成片段；如果 ffmpeg 不可用或 dry_run 片段不是标准 mp4，会写入合并占位文件，保证 manifest 与下游合约可检查。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/07_storyboard_image/image_manifest.json
workspace/projects/{project_id}/07_storyboard_image/images/shot_001.png ...
workspace/projects/{project_id}/08_audio/final_audio.wav
workspace/projects/{project_id}/08_audio/audio_timeline.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/07_storyboard_image/image_manifest.json
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/final_audio.wav
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/audio_timeline.json
```

---

## 输出

```text
09_video/video_manifest.json
09_video/video_meta.json
09_video/video_plan.json
09_video/resume_manifest.json
09_video/merge_result.json
09_video/final_video.mp4
09_video/clips/clip_0001.mp4 ...
09_video/intermediate/09A_video_segment_plan.json
09_video/intermediate/09B_ltx23_execution.json
09_video/intermediate/09C_resume_scan.json
09_video/intermediate/09D_final_merge.json
```

---

## 环境变量

### 执行模式

```text
AI_DRAMA_VIDEO_EXECUTION_MODE=dry_run|execute
```

默认：

```text
dry_run
```

### 视频切片

```text
AI_DRAMA_VIDEO_SEGMENT_SECONDS=10|12
AI_DRAMA_VIDEO_FPS=24
AI_DRAMA_VIDEO_WIDTH=1280
AI_DRAMA_VIDEO_HEIGHT=720
AI_DRAMA_VIDEO_FRAMES_FORMULA=int(a*b/8)*8+1
AI_DRAMA_VIDEO_OVERLAP_FRAMES=0
```

### ComfyUI / LTX2.3

```text
AI_DRAMA_COMFYUI_BASE_URL=http://127.0.0.1:8188
AI_DRAMA_VIDEO_COMFYUI_WORKFLOW=workflow_api.json
AI_DRAMA_VIDEO_COMFYUI_TIMEOUT_SEC=3600
AI_DRAMA_COMFYUI_CLIENT_ID=ai_drama_09_video_ltx23
```

### 关键节点映射

09 使用语义节点注入方式适配你本地已验证的 LTX2.3 音频切割工作流。格式：

```text
环境变量=node_id:input_key
```

常用映射：

```text
AI_DRAMA_VIDEO_NODE_PROMPT=2116:text
AI_DRAMA_VIDEO_NODE_IMAGE_PATH=你的图片加载节点:image_path
AI_DRAMA_VIDEO_NODE_AUDIO_PATH=2170:audio_path
AI_DRAMA_VIDEO_NODE_PROJECT_NAME=2170:project_name
AI_DRAMA_VIDEO_NODE_BASE_PATH=2170:base_path
AI_DRAMA_VIDEO_NODE_CURRENT_CHUNK=2170:current_chunk
AI_DRAMA_VIDEO_NODE_CURRENT_SEGMENT_INDEX=2146:current_segment_index
AI_DRAMA_VIDEO_NODE_DURATION=2170:duration
AI_DRAMA_VIDEO_NODE_FPS=2148:帧率_fps
AI_DRAMA_VIDEO_NODE_WIDTH=2148:宽度
AI_DRAMA_VIDEO_NODE_HEIGHT=2148:高度
AI_DRAMA_VIDEO_NODE_FRAME_COUNT=2123:运行帧数
AI_DRAMA_VIDEO_NODE_OVERLAP_FRAMES=2146:overlap_frames
AI_DRAMA_VIDEO_NODE_OUTPUT_PREFIX=2186:文件前缀_Prefix
```

由于你的工作流可能是桌面版 workflow JSON，而不是 API JSON，实际 execute 前建议先在 ComfyUI 里导出 API 格式 workflow，再把对应 node_id/input_key 写到环境变量。

### 断点与合并

```text
AI_DRAMA_VIDEO_FORCE_RERUN=0|1
AI_DRAMA_VIDEO_AUTO_MERGE=1|0
AI_DRAMA_FFMPEG=ffmpeg
```

---

## 与上传的 LTX2.3 工作流思路对应

本模块按你本地已验证的工作流思路实现：

```text
输入：分镜图片文件夹 / image_manifest
输入：整章完整音频 final_audio.wav
按 current_chunk / current_segment_index 进行音频切片
通过 AudioPaddingSlicer 一类节点得到当前段音频和帧数
通过 KeyframeRouter / LTXVImgToVideoInplace(KJ) 绑定图片
通过 ResumeScanner 类节点支持断点续跑
通过 VideoSaveMerge 类节点保存视频段并最终合并
```

仓库代码侧不硬编码某个自制节点名称，避免你的本地节点版本变化导致 09 失效；而是通过 `AI_DRAMA_VIDEO_NODE_*` 做语义注入。

---

## 最高规则

```text
09 只负责让 07 分镜图按 08 音频节奏动起来。
09 不新增角色、不新增场景、不新增道具。
09 不改 07 图片内容。
09 不改 08 音频内容。
09 失败时优先重跑缺失视频段，不回滚 06/07/08。
09 加载 LTX2.3 前释放图片/音频资源，完成后释放视频资源。
```

---

## 推荐测试顺序

先 dry_run：

```bash
set AI_DRAMA_VIDEO_EXECUTION_MODE=dry_run
set AI_DRAMA_VIDEO_SEGMENT_SECONDS=10
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 09_video
```

再 execute：

```bash
set AI_DRAMA_VIDEO_EXECUTION_MODE=execute
set AI_DRAMA_COMFYUI_BASE_URL=http://127.0.0.1:8188
set AI_DRAMA_VIDEO_COMFYUI_WORKFLOW=你的LTX2.3_API工作流.json
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 09_video
```
