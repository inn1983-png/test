# 08 音频系统

## 模块定位

音频系统负责把剧本中的对白、OS、留白、情绪、语速、音色配置生成完整音频。

它不负责改写剧情，不负责生成分镜图，不负责生成视频。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/02_script_writer/script.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
workspace/books/{book_id}/shared_assets/voice_library/voices.json
workspace/books/{book_id}/shared_assets/voice_library/samples/
```

---

## 输出

```text
08_audio/audio_script.json
08_audio/final_audio.wav
08_audio/audio_manifest.json
```

正式运行时输出到：

```text
workspace/projects/{project_id}/08_audio/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/
```

---

## 核心任务

1. 读取剧本中的对白、OS、留白
2. 生成音频脚本 audio_script.json
3. 为不同角色匹配音色
4. 控制语气、情绪、停顿、语速
5. 调用本地 TTS 模型
6. 输出完整音频 final_audio.wav
7. 记录每句台词的时间信息

---

## 推荐 audio_script 字段

```json
{
  "line_id": "line_001",
  "speaker": "OS",
  "text": "",
  "emotion": "压抑",
  "speed": "normal",
  "pause_after": 0.8,
  "voice_id": "voice_os_001"
}
```

---

## 本地模型/工具

本模块未来可接入：

```text
CosyVoice2
IndexTTS
GPT-SoVITS
其他本地 TTS 模型
```

---

## 最高规则

- 不改写剧本正文
- 不改变角色说话人
- 留白必须体现为停顿
- 生成完音频后必须释放显存
- 音色库属于共享资产，不要放进单章目录

---

## 与其他模块关系

```text
02_script_writer → 08_audio → 09_video / 10_final_assembly
```
