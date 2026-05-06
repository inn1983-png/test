# 10 成片拼接系统

## 模块定位

成片拼接系统负责把视频片段、音频、字幕、封面等素材整合为最终成片。

它是最终包装层，不负责写剧本、不负责生成分镜图、不负责生成视频片段。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/09_video/clips/
workspace/projects/{project_id}/09_video/video_manifest.json
workspace/projects/{project_id}/08_audio/final_audio.wav
workspace/projects/{project_id}/02_script_writer/script.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/09_video/clips/
workspace/books/{book_id}/chapters/{chapter_id}/09_video/video_manifest.json
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/final_audio.wav
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
```

---

## 输出

```text
10_final_assembly/final.mp4
10_final_assembly/cover.png
10_final_assembly/subtitles.srt
10_final_assembly/final_manifest.json
```

正式运行时输出到：

```text
workspace/projects/{project_id}/10_final_assembly/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/10_final_assembly/
```

---

## 核心任务

1. 按顺序拼接视频片段
2. 对齐完整音频
3. 生成或导入字幕
4. 添加封面、片头、片尾
5. 输出最终成片
6. 生成 final_manifest.json

---

## 本地工具

本模块未来可接入：

```text
FFmpeg
MoviePy
本地字幕生成工具
本地封面生成工具
```

---

## 最高规则

- 不改写剧情
- 不重新生成视频片段
- 不改变角色资产
- 不改变分镜图
- 只负责最终拼接和包装

---

## 与其他模块关系

```text
09_video + 08_audio + subtitles → 10_final_assembly → final.mp4
```
