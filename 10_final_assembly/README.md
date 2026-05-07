# 10 最终成片包装层

## 模块定位

`10_final_assembly` 是最终成片包装层，只读取 `09_video` 与 `08_audio` 的既有产物，导出最终成片。

```text
08_audio + 09_video → 10_final_assembly → final.mp4
```

最高边界：

```text
不调用 LLM。
不调用 LTX。
不调用 ComfyUI。
不生成新视频片段。
不改写剧本。
不重做分镜图。
不重配音。
只做最终封装、音频替换、字幕复制 / 可选烧录、manifest 输出。
```

---

## 正式入口

```bash
python 10_final_assembly/run_staged.py
```

在总控中运行：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 10_final_assembly
```

---

## 阶段

```text
10A input_check
10B video_prepare
10C audio_subtitle_align
10D final_export
```

### 10A：输入检查

读取：

```text
09_video/video_manifest.json
09_video/final_video.mp4 或 09_video/clips/*.mp4 / video_segments[].output_clip_path
08_audio/final_audio.wav
08_audio/subtitle.srt
08_audio/subtitle.ass
```

核心规则：

```text
优先使用 09_video/final_video.mp4。
如果没有 final_video.mp4，则从 video_manifest.video_segments / segments / clips 收集 clip 路径。
如果 manifest 没有可用 clip 路径，则按 09_video/clips/*.mp4 扫描。
final_audio.wav 永远以 08_audio/final_audio.wav 为准。
subtitle.srt / subtitle.ass 只从 08_audio 复制，不默认烧录。
```

输出：

```text
10_final_assembly/intermediate/10A_input_check.json
```

### 10B：视频准备

输出：

```text
10_final_assembly/prepared/prepared_video.mp4
10_final_assembly/intermediate/10B_video_prepare.json
```

核心逻辑：

```text
如果 09_video/final_video.mp4 有效：复制为 prepared_video.mp4。
否则使用 ffmpeg concat 合并 09 clip。
如果 AI_DRAMA_FINAL_DRY_RUN=1 或 ffmpeg 不可用：写入可检查占位 prepared_video.mp4。
```

### 10C：音频字幕对齐

输出：

```text
10_final_assembly/subtitles/subtitle.srt
10_final_assembly/subtitles/subtitle.ass
10_final_assembly/intermediate/10C_audio_subtitle_align.json
```

核心逻辑：

```text
最终音频默认使用 08_audio/final_audio.wav。
字幕只复制，不烧录。
字幕缺失不阻断 final.mp4，只在质量报告中提示。
```

### 10D：最终导出

输出：

```text
10_final_assembly/final.mp4
10_final_assembly/final_manifest.json
10_final_assembly/final_meta.json
10_final_assembly/intermediate/10D_final_export.json
```

核心逻辑：

```text
默认用 ffmpeg 把 prepared_video.mp4 与 08_audio/final_audio.wav mux 成 final.mp4。
默认不烧录字幕。
设置 AI_DRAMA_FINAL_BURN_SUBTITLES=1 后，优先烧录 subtitle.ass，没有 ass 时烧录 subtitle.srt。
如果 final.mp4 已存在且有效，默认跳过重导出。
设置 AI_DRAMA_FINAL_FORCE_RERUN=1 后强制重导出。
```

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/09_video/video_manifest.json
workspace/projects/{project_id}/09_video/final_video.mp4
workspace/projects/{project_id}/09_video/clips/clip_0001.mp4 ...
workspace/projects/{project_id}/08_audio/final_audio.wav
workspace/projects/{project_id}/08_audio/subtitle.srt
workspace/projects/{project_id}/08_audio/subtitle.ass
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/09_video/video_manifest.json
workspace/books/{book_id}/chapters/{chapter_id}/09_video/final_video.mp4
workspace/books/{book_id}/chapters/{chapter_id}/09_video/clips/clip_0001.mp4 ...
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/final_audio.wav
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/subtitle.srt
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/subtitle.ass
```

---

## 输出

```text
10_final_assembly/final.mp4
10_final_assembly/final_manifest.json
10_final_assembly/final_meta.json
10_final_assembly/prepared/prepared_video.mp4
10_final_assembly/subtitles/subtitle.srt
10_final_assembly/subtitles/subtitle.ass
10_final_assembly/intermediate/10A_input_check.json
10_final_assembly/intermediate/10B_video_prepare.json
10_final_assembly/intermediate/10C_audio_subtitle_align.json
10_final_assembly/intermediate/10D_final_export.json
```

---

## 环境变量

```text
AI_DRAMA_FFMPEG=ffmpeg
AI_DRAMA_FFPROBE=ffprobe
AI_DRAMA_FINAL_DRY_RUN=0|1
AI_DRAMA_FINAL_FORCE_RERUN=0|1
AI_DRAMA_FINAL_BURN_SUBTITLES=0|1
AI_DRAMA_FINAL_MIN_VALID_BYTES=1024
```

默认值：

```text
AI_DRAMA_FINAL_DRY_RUN=0
AI_DRAMA_FINAL_FORCE_RERUN=0
AI_DRAMA_FINAL_BURN_SUBTITLES=0
AI_DRAMA_FINAL_MIN_VALID_BYTES=1024
```

---

## ffprobe 校验

10B 和 10D 阶段导出视频后，自动调用 ffprobe 校验：

```text
has_video：是否包含视频流
has_audio：是否包含音频流
duration_seconds：视频时长
stream_count：流数量
streams：每个流的 codec_type / codec_name / width / height
format：format_name / size / bit_rate / duration
```

校验失败（无视频流）时标记 needs_review。

ffprobe 不可用时不阻断流程，只在 ffprobe_validation 中记录 error。

---

## dry_run 策略

`10_final_assembly` 支持 dry_run：

```bash
set AI_DRAMA_FINAL_DRY_RUN=1
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 10_final_assembly
```

dry_run 会生成：

```text
prepared/prepared_video.mp4 占位文件
final.mp4 占位文件
final_manifest.json
final_meta.json
```

这样即使本机没有 ffmpeg，也能先检查 08/09 到 10 的合约是否打通。

---

## 断点策略

```text
final.mp4 已存在且大于 AI_DRAMA_FINAL_MIN_VALID_BYTES 时，默认跳过重导出。
需要强制重导出时设置 AI_DRAMA_FINAL_FORCE_RERUN=1。
```

---

## 关于公开剪辑项目接入

当前 10 默认使用 FFmpeg，因为它最适合最终包装层的确定性需求：concat、mux、字幕烧录都可控，且不会把 10 变成新的创作层。

后续可作为插件接入：

```text
MoviePy：适合 Python 内剪辑、标题、合成、效果，但字幕合成和复杂重编码可能较慢。
Editly：适合 Node.js 声明式剪辑、片头片尾、转场、图文包装，但会新增 Node/npm 依赖。
```

建议接入方式：

```text
10_final_assembly/core/editing_plugins/
  moviepy_plugin.py
  editly_plugin.py
```

但默认路径仍保持：

```text
FFmpeg deterministic assembly first.
```

---

## 最高规则

```text
10 只做最终包装。
10 不新增镜头。
10 不新增角色。
10 不改变 09 视频画面内容。
10 不改变 08 音频内容。
10 默认不烧录字幕，只复制字幕。
10 失败时只修复最终包装问题，不回滚 01–09，除非上游关键产物缺失。
```
