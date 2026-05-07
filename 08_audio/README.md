# 08 配音生成系统

## 模块定位

08_audio 是 AUDIO_PHASE，负责把 02_script_writer 输出的对白、OS、旁白、留白转成完整音频。

它不负责改写剧情，不负责生成分镜图，不负责生成视频。

当前已接入本地根目录 `index-tts` / IndexTTS2 适配器：项目仓库只保存调用代码和 manifest，不保存 TTS 权重。

本轮已吸收 `TxtovideoAudio` 的核心音频驱动规则：

```text
N：旁白，固定旁白音色，弱情绪，不强制口型。
D：角色对白，角色音色，保留较强情绪，可用于口型。
M：心理 OS，角色音色或 OS 音色，中等情绪，不强制口型。
S：静音留白，只生成静音段。
```

08 的目标是从真实音频时长出发，为 09 的 6–12 秒视频单元规划服务。

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

同时支持 `TxtovideoAudio` 风格标记：

```text
【N|emotion|speed】旁白文本
【D:角色名|emotion|speed】角色对白
【M:角色名|emotion|speed】心理 OS
【S:秒数】
```

如果 02 只输出了 `script_text` / `final_script` / `content`，08 会优先尝试解析上面的 N/D/M/S 标记；如果没有标记，才生成 fallback 旁白音频段。

---

## 音色库绑定

08 会从以下位置读取音色库：

```text
AI_DRAMA_VOICE_MAP 指定的 json
AI_DRAMA_SHARED_ASSETS_DIR/voice_library/voices.json
AI_DRAMA_SHARED_ASSETS_DIR/voice_library/voice_map.json
shared_assets/voice_library/voices.json
shared_assets/voice_library/voice_map.json
```

推荐格式：

```json
{
  "schema_version": "1.0",
  "default_voice_id": "narrator_default",
  "narrator": {
    "voice_id": "narrator_default",
    "spk_audio_prompt": "examples/voice_07.wav",
    "description": "默认旁白音色"
  },
  "roles": {
    "张捕头": {
      "voice_id": "zhang_butou",
      "spk_audio_prompt": "voice_samples/zhang_butou.wav",
      "description": "中年男声，粗粝，压迫感"
    },
    "女主": {
      "voice_id": "female_lead",
      "spk_audio_prompt": "voice_samples/female_lead.wav",
      "description": "年轻女声，冷静，克制"
    }
  },
  "fallbacks": {
    "male": "narrator_default",
    "female": "narrator_default",
    "unknown": "narrator_default"
  }
}
```

`spk_audio_prompt` 可以是相对 `index-tts` 的路径，也可以是绝对路径。

---

## 输出

```text
08_audio/final_audio.wav
08_audio/audio_manifest.json
08_audio/audio_meta.json
08_audio/audio_timeline.json
08_audio/subtitle.srt
08_audio/subtitle.ass
08_audio/intermediate/08A_audio_queue.json
08_audio/intermediate/08B_tts_segment_plan.json
08_audio/intermediate/08C_tts_execution.json
08_audio/intermediate/08D_final_mix.json
08_audio/segments/audio_seg_0001.wav ...
```

`final_audio.wav` 是 09_video 的关键依赖。

`audio_timeline.json` 给 09_video 使用，用于按真实音频时长规划 6–12 秒视频单元。

---

## 阶段设计

```text
08A audio_queue_build：从 02 剧本提取对白 / OS / 旁白 / 静音留白队列，不重写剧情。
08B voice_emotion_binding_and_tts_plan：绑定音色库、映射情绪、建立 TTS 分段计划。
08C tts_execution：dry_run 生成真实静音 WAV；execute 调用本地 IndexTTS2。
08D final_mix_timeline_subtitle：拼接分段音频和停顿，输出 final_audio.wav、audio_timeline.json、subtitle.srt、subtitle.ass。
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
set AI_DRAMA_VOICE_MAP=shared_assets/voice_library/voices.json
set AI_DRAMA_TTS_FP16=1
set AI_DRAMA_TTS_DEEPSPEED=0
set AI_DRAMA_TTS_CUDA_KERNEL=0
set AI_DRAMA_TTS_EMO_ALPHA=0.6
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 08_audio
```

IndexTTS2 README 推荐使用 `uv run`，所以 execute 模式会在 `index-tts` 目录下用 `uv run` 执行临时推理脚本。

---

## 情绪控制

当前先把中文情绪映射为更稳定的 `emo_text` 和 `emo_alpha`：

```text
愤怒 → 愤怒，压低声音，带有克制的火气
压抑 → 压抑，低沉，克制，带一点悲凉
恐惧 → 恐惧，紧张，急促，带颤抖
震惊 → 震惊，短促，难以置信
冷笑 → 冷笑，讥讽，平静中带轻蔑
平静 / calm → 平静，自然，清晰
```

并按类型限制情绪强度：

```text
N 旁白：弱情绪
D 对白：完整情绪
M 心理 OS：中等情绪
S 静音：无情绪
```

如果提供独立情绪参考音频：

```bash
set AI_DRAMA_TTS_DEFAULT_EMO_AUDIO=examples/emo_sad.wav
```

---

## 后处理

默认不破坏 `final_audio.wav`。

如需响度归一化：

```bash
set AI_DRAMA_AUDIO_NORMALIZE=1
```

系统会尝试调用 ffmpeg 额外生成：

```text
08_audio/final_audio_normalized.wav
```

---

## 最高规则

```text
不改写剧本正文。
不改变角色说话人。
N/D/M/S 标记优先保持原顺序。
旁白 N 使用 narrator 音色。
对白 D 使用角色音色，可用于口型。
心理 OS/M 使用角色音色或 OS 音色，中等情绪，不强制口型。
留白 S 必须体现为静音段。
失败段只建议局部重跑 failed_audio_segments，不回滚 02。
如果单条 voice_line 加起势和末帧留白后超过 12 秒，优先回到 02 拆句，不在 09 硬救。
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
08_audio/audio_timeline.json
```
