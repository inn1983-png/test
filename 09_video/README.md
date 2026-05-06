# 09 视频生成系统

## 模块定位

视频生成系统负责读取分镜图和音频，调用本地视频模型生成视频片段。

它是视频执行层，不负责写剧本、不负责生成角色、不负责重新设计分镜。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/07_storyboard_image/images/
workspace/projects/{project_id}/07_storyboard_image/image_manifest.json
workspace/projects/{project_id}/08_audio/final_audio.wav
workspace/projects/{project_id}/08_audio/audio_manifest.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/07_storyboard_image/images/
workspace/books/{book_id}/chapters/{chapter_id}/07_storyboard_image/image_manifest.json
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/final_audio.wav
workspace/books/{book_id}/chapters/{chapter_id}/08_audio/audio_manifest.json
```

---

## 输出

```text
09_video/clips/clip_001.mp4
09_video/clips/clip_002.mp4
09_video/video_manifest.json
```

正式运行时输出到：

```text
workspace/projects/{project_id}/09_video/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/09_video/
```

---

## 核心任务

1. 读取分镜图文件夹
2. 读取音频文件
3. 按音频或配置切分生成视频片段
4. 调用本地视频模型
5. 输出视频片段
6. 记录每段视频对应的图片、音频时间、生成参数
7. 生成 video_manifest.json

---

## 本地模型/工具

本模块未来可接入：

```text
LTX2.3
Wan / HunyuanVideo / 其他本地图生视频模型
ComfyUI 视频工作流
Qwen-VL 反推提示词
```

---

## 最高规则

- 视频系统只负责“动起来”
- 不负责补剧情
- 不负责重新创造角色
- 不负责修改分镜图内容
- 分镜图质量由 07 负责
- 音频节奏由 08 负责
- 本模块完成后必须释放显存

---

## 与其他模块关系

```text
07_storyboard_image + 08_audio → 09_video → 10_final_assembly
```
