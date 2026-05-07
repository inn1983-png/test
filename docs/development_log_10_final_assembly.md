# 10_final_assembly 开发记录

本记录补充 `docs/development_log.md`，用于记录本轮 10 最终成片包装层的落地细节。

## 本轮新增

```text
10_final_assembly 已从旧成片拼接说明升级为真实最终包装层。
10 不调用 LLM，不调用 LTX，不调用 ComfyUI，不生成新视频片段。
10 只读取 09_video 与 08_audio 的既有产物并导出 final.mp4。
```

## 新增文件

```text
10_final_assembly/module_config.json
10_final_assembly/run_staged.py
10_final_assembly/core/stage_runner.py
10_final_assembly/core/ffmpeg_client.py
10_final_assembly/core/quality_checker.py
10_final_assembly/core/schema_validator.py
```

## 阶段

```text
10A input_check：读取 09_video/video_manifest.json、09_video/final_video.mp4 或 clips、08_audio/final_audio.wav、08_audio/subtitle.srt / subtitle.ass。
10B video_prepare：优先复制 09_video/final_video.mp4；没有则按 video_segments / clips 用 ffmpeg concat 合并；dry_run 或无 ffmpeg 时写占位 prepared_video.mp4。
10C audio_subtitle_align：最终音频以 08_audio/final_audio.wav 为准；字幕从 08_audio 复制到 10/subtitles。
10D final_export：输出 final.mp4、final_manifest.json、final_meta.json；默认 mux 视频+音频，不烧录字幕。
```

## 关键环境变量

```text
AI_DRAMA_FFMPEG=ffmpeg
AI_DRAMA_FINAL_DRY_RUN=0|1
AI_DRAMA_FINAL_FORCE_RERUN=0|1
AI_DRAMA_FINAL_BURN_SUBTITLES=0|1
AI_DRAMA_FINAL_MIN_VALID_BYTES=1024
```

## 字幕规则

```text
默认不烧录字幕，只复制 subtitle.srt / subtitle.ass。
设置 AI_DRAMA_FINAL_BURN_SUBTITLES=1 后，优先烧录 subtitle.ass，没有 ass 时烧录 subtitle.srt。
```

## 断点规则

```text
final.mp4 已存在且有效时默认跳过重导出。
设置 AI_DRAMA_FINAL_FORCE_RERUN=1 后强制重新导出。
```

## dry_run 规则

```text
AI_DRAMA_FINAL_DRY_RUN=1 时，即使 ffmpeg 不可用，也会生成 prepared_video.mp4 占位、final.mp4 占位、final_manifest.json、final_meta.json，方便检查 08/09/10 合约。
```

## module_contracts 更新

```text
10_final_assembly requires:
- 09_video/video_manifest.json
- 08_audio/final_audio.wav
- 可选 09_video/final_video.mp4
- 可选 09_video/clips
- 可选 08_audio/subtitle.srt
- 可选 08_audio/subtitle.ass

10_final_assembly produces:
- final.mp4
- final_manifest.json
- final_meta.json
```

## 公开剪辑项目接入建议

```text
默认路径保持 FFmpeg deterministic assembly。
MoviePy 可作为 Python 插件用于标题、片头片尾、复杂合成。
Editly 可作为 Node 插件用于声明式剪辑、转场、图文包装。
插件建议放入 10_final_assembly/core/editing_plugins/，但不得改变 10 的最高边界：不新增镜头、不创作新内容。
```
