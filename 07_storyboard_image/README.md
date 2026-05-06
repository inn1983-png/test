# 07 分镜图生成系统

## 模块定位

分镜图生成系统负责把分镜表、角色参考图、场景参考图、道具参考图融合成单帧分镜图。

它是图像执行层，不负责写剧本，不负责重新理解剧情。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/06_storyboard/storyboard.json
workspace/projects/{project_id}/03_character_library/characters.json
workspace/projects/{project_id}/04_scene_library/scenes.json
workspace/projects/{project_id}/05_prop_library/props.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/06_storyboard/storyboard.json
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/characters/images/
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/scenes/images/
workspace/books/{book_id}/shared_assets/props/props.json
workspace/books/{book_id}/shared_assets/props/images/
```

---

## 输出

```text
07_storyboard_image/images/shot_001.png
07_storyboard_image/images/shot_002.png
07_storyboard_image/image_manifest.json
```

正式运行时输出到：

```text
workspace/projects/{project_id}/07_storyboard_image/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/07_storyboard_image/
```

---

## 核心任务

1. 读取 storyboard.json
2. 根据每个分镜引用角色、场景、道具资产
3. 调用本地 ComfyUI / 生图工作流
4. 生成单帧分镜图
5. 记录每张图对应的分镜 ID、资产引用、生成参数
6. 生成 image_manifest.json

---

## 关键原则

- 场景优先稳定
- 角色必须来自角色库
- 道具必须来自道具库
- 不允许图像系统凭空新增人物
- 不允许出现现代物品污染古代场景
- 每个分镜图应尽量独立稳定
- 本模块完成后必须释放显存

---

## 本地模型/工具

本模块未来可以接入：

```text
ComfyUI
Flux / SD / Pony / 其他本地生图模型
Qwen-VL 图像反推
IPAdapter / ControlNet / PuLID / InstantID 等参考图控制方案
```

具体模型可以替换，但输出协议不要随意改变。

---

## 与其他模块关系

```text
06_storyboard + shared_assets → 07_storyboard_image → 09_video
```
