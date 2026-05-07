# 08 配音生成系统

## 模块定位

08_audio 是 AUDIO_PHASE，负责把 02_script_writer 输出的对白、OS、旁白、留白转成完整音频。

它不负责改写剧情，不负责生成分镜图，不负责生成视频。

当前已接入本地根目录 `index-tts` / IndexTTS2 适配器：项目仓库只保存调用代码和 manifest，不保存 TTS 权重。

---

## 输入

正式 pipeline 输入：

```text
workspace/projects/{project_id}/02_script_writer/script.json
```

或长篇章节模式：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
```

08 会优先从以下字段提取音频队列：

```text
voice_lines
audio_lines
dialogue_lines
narration_lines
segments[].voice_lines / lines / dialogues / narrations
visual_dramatic_units[].voice_lines / dialogue_lines / lines
```

如果 02 只输出了 `script_text` / `final_script` / `content`，08 会生成一个 fallback 旁白音频段，保证流程闭环，但会在质量报告里体现风险。

---

## 输出

```text
08_audio/final_audio.wav
08_audio/audio_manifest.json
08_audio/audio_meta.json
08_audio/intermediate/08A_audio_queue.json
08_audio/intermediate/08B_tts_segment_plan.json
08_audio/intermediate/08C_tts_execution.json
08_audio/intermediate/08D_final_mix.json
08_audio/segments/audio_seg_0001.wav ...
```

`final_audio.wav` 是 09_video 的关键依赖。

---

## 阶段设计

```text
08A audio_queue_build：从 02 剧本提取对白 / OS / 旁白队列，不重写剧情。
08B tts_segment_plan：为每条音频行建立独立 TTS 分段，检查 index-tts 环境。
08C tts_execution：dry_run 生成真实静音 WAV；execute 调用本地 IndexTTS2。
08D final_mix：线性拼接分段音频和停顿，输出 final_audio.wav。
```

每个阶段都会输出 `stage_quality`，并写入 `stage_status`，方便 Web UI 展示每一步具体在做什么。

---

## 本地 index-tts 放置规则

用户已在项目本地根目录放置：

```text
index-tts/
```

08 默认按以下路径查找：

```text
index-tts/checkpoints/config.yaml
index-tts/checkpoints/...
index-tts/examples/voice_07.wav
```

如果你的路径不同，可用环境变量覆盖：

```bash
set AI_DRAMA_INDEX_TTS_ROOT=D:\Txtovideo\index-tts
set AI_DRAMA_TTS_DEFAULT_VOICE=examples/voice_07.wav
```

注意：`AI_DRAMA_TTS_DEFAULT_VOICE` 可以是相对 `index-tts` 的路径，也可以是绝对路径。

---

## 运行模式

默认：

```bash
set AI_DRAMA_AUDIO_EXECUTION_MODE=dry_run
```

`dry_run` 会生成真实可读取的静音 WAV 文件，用于测试 08→09 依赖、Web UI 展示和 pipeline 闭环。

真实调用 IndexTTS2：

```bash
set AI_DRAMA_AUDIO_EXECUTION_MODE=execute
set AI_DRAMA_INDEX_TTS_ROOT=index-tts
set AI_DRAMA_TTS_DEFAULT_VOICE=examples/voice_07.wav
set AI_DRAMA_TTS_FP16=1
set AI_DRAMA_TTS_DEEPSPEED=0
set AI_DRAMA_TTS_CUDA_KERNEL=0
set AI_DRAMA_TTS_EMO_ALPHA=0.6
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 08_audio
```

IndexTTS2 README 推荐使用 `uv run`，所以 execute 模式会在 `index-tts` 目录下用 `uv run` 执行临时推理脚本。

---

## 情绪控制

当前默认使用：

```text
use_emo_text=True
emo_text=当前音频段 emotion 字段
emo_alpha=AI_DRAMA_TTS_EMO_ALPHA，默认 0.6
use_random=False
```

如果提供独立情绪参考音频：

```bash
set AI_DRAMA_TTS_DEFAULT_EMO_AUDIO=examples/emo_sad.wav
```

后续可扩展：角色音色库、OS 专用音色、男女角色多音色、响度归一化、BGM、音效、字幕时间轴。

---

## 最高规则

```text
不改写剧本正文。
不改变角色说话人。
留白和 pause_after_seconds 必须体现为停顿。
失败段只建议局部重跑 failed_audio_segments，不回滚 02。
08 完成后，进入 09 前由总控释放 audio resources。
TTS 权重和音色样本属于本地资源 / shared_assets，不提交进仓库。
```

---

## 与其他模块关系

```text
02_script_writer → 08_audio → 09_video
```

09_video 同时依赖：

```text
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
```
