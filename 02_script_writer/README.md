# 02 剧本改编系统

## 模块定位

剧本改编系统负责把小说解析结果改编为适合短视频 / 横屏短剧 / AI 漫剧生产的剧本。

它是成片留存的核心模块，但它不负责角色资产、不负责分镜图、不负责视频生成。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/01_novel_parser/novel_analysis.json
workspace/projects/{project_id}/01_novel_parser/events.json
workspace/projects/{project_id}/01_novel_parser/conflict_map.json
workspace/projects/{project_id}/01_novel_parser/emotion_curve.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/novel_analysis.json
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/events.json
workspace/books/{book_id}/global_memory/book_summary.json
workspace/books/{book_id}/global_memory/style_bible.md
```

---

## 输出

```text
02_script_writer/script.json
02_script_writer/script.txt
02_script_writer/script_meta.json
```

正式运行时输出到项目运行目录：

```text
workspace/projects/{project_id}/02_script_writer/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/
```

---

## 核心任务

1. 根据小说解析结果改编剧本
2. 保留关键事件，不得过度压缩
3. 保留高刺激冲突点
4. 生成对白、OS、留白、动作、情绪
5. 为后续音频系统保留说话人、语气、停顿信息
6. 为后续分镜系统保留画面动作锚点

---

## 输出风格

推荐结构：

```text
【OS】旁白 / 心理独白
【角色名】对白
【留白】节奏停顿
【动作】画面动作
【情绪】语气和表演方向
```

---

## 禁止事项

- 不生成角色图片
- 不生成场景图片
- 不直接调用 ComfyUI
- 不生成视频
- 不擅自改动角色库
- 不把多个关键事件压成一句话

---

## 与其他模块关系

```text
01_novel_parser → 02_script_writer → 06_storyboard / 08_audio
```

03/04/05 资产库系统可以与本模块并行或在本模块之后运行。
