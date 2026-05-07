# 07 分镜图生成系统

## 模块定位

`07_storyboard_image` 是图片执行阶段，不再是一个简单的“分镜图任务生成器”，而是一个完整的图片生产子系统。

它负责把 `06_storyboard/storyboard.json` 中的单帧分镜、角色定妆引用、角色造型引用、场景引用、道具引用，拆成以下生产链路：

```text
07P 计划与依赖图
07A 角色定妆图
07B 角色造型图 / 换装图
07C 场景 / 道具参考图
07D 正式单帧分镜图
07E 汇总、注册表、总检、局部重跑计划
```

核心原则：

```text
先锁脸，再换装，最后生成分镜图。
07 不重新写剧情。
07 不重新规划分镜。
07 不新增 03/04/05 资产。
07 只把 06 已绑定的结构化分镜转成图片执行任务。
```

---

## 正式入口

```bash
python 07_storyboard_image/run_staged.py
```

也可以由总控运行：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 07_storyboard_image
```

---

## 输入

必需输入：

```text
06_storyboard/storyboard.json
```

可选输入，用于按需生成定妆图、造型图、场景图、道具图：

```text
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
```

06 中每帧必须已经绑定：

```text
scene.canonical_scene_name
characters[].canonical_name
characters[].costume_id
characters[].appearance_asset_key
characters[].character_lock_reference
characters[].wearable_props
props[].canonical_prop_name
```

---

## 输出

最终关键产物：

```text
07_storyboard_image/image_manifest.json
07_storyboard_image/image_meta.json
07_storyboard_image/character_lock_manifest.json
07_storyboard_image/appearance_manifest.json
07_storyboard_image/reference_asset_manifest.json
07_storyboard_image/dependency_index.json
07_storyboard_image/asset_image_registry.json
07_storyboard_image/storyboard_image_meta.json
```

阶段输出：

```text
07_storyboard_image/intermediate/07P_plan.json
07_storyboard_image/intermediate/07A_character_lock.json
07_storyboard_image/intermediate/07B_character_appearance.json
07_storyboard_image/intermediate/07C_reference_assets.json
07_storyboard_image/intermediate/07D_storyboard_frame.json
07_storyboard_image/intermediate/07E_finalize.json
```

图片目录：

```text
07_storyboard_image/images/character_lock/
07_storyboard_image/images/character_appearance/
07_storyboard_image/images/scene_reference/
07_storyboard_image/images/prop_reference/
07_storyboard_image/images/storyboard/
```

---

## 阶段设计

### 07P_plan

计划与依赖图阶段。

职责：

```text
读取 06 storyboard + 03/04/05 assets
计算哪些角色需要定妆图
计算哪些 appearance_asset_key 需要造型图
计算哪些场景 / 道具需要参考图
计算每个 frame 依赖哪些角色造型、场景、道具
生成 dependency_index，用于局部重跑和失效传播
```

输出：

```text
character_lock_tasks
appearance_tasks
reference_asset_tasks
storyboard_frame_tasks
dependency_index
```

---

### 07A_character_lock

角色定妆图阶段。

本质：

```text
文生图 → 角色定妆图
```

目标：

```text
单人
锁脸
固定性别 / 年龄 / 气质
背景干净
不追求剧情动作
```

输出：

```text
character_lock_manifest.json
images/character_lock/*.png
```

---

### 07B_character_appearance

角色造型图 / 换装图阶段。

本质：

```text
定妆图 + costume_id + wearable_props → 角色造型图
```

目标：

```text
同一张脸
指定服装版本
指定常驻穿戴物
给后续分镜图作为稳定角色参考图
```

输出：

```text
appearance_manifest.json
images/character_appearance/*.png
```

---

### 07C_reference_assets

场景 / 道具参考图阶段。

职责：

```text
只处理本章 / 本次 06 分镜实际用到的场景和关键道具
可以生成，也可以登记已有参考图
不给不存在于 04/05 的资产硬造新名字
```

输出：

```text
reference_asset_manifest.json
images/scene_reference/*.png
images/prop_reference/*.png
```

---

### 07D_storyboard_frame

正式单帧分镜图阶段。

本质：

```text
场景参考图 + 角色造型图 + 道具参考图 + 06 分镜结构 → 正式分镜图
```

执行策略：

```text
锚点帧优先
普通帧可引用锚点帧 / 上一帧
失败时优先只重跑失败帧
```

输出：

```text
image_manifest.json
images/storyboard/shot_001.png
images/storyboard/shot_002.png
...
```

---

### 07E_finalize

总检、注册表、局部重跑计划。

职责：

```text
汇总定妆图、造型图、参考图、分镜图
生成 asset_image_registry
生成 dependency_index
检查缺图和失败任务
生成 retry_plan
输出 storyboard_image_meta
```

输出：

```text
asset_image_registry.json
dependency_index.json
storyboard_image_meta.json
```

---

## 执行模式

### 1. dry_run 默认模式

不调用 ComfyUI，只生成任务清单、manifest 和预期图片路径。

```bash
set AI_DRAMA_IMAGE_EXECUTION_MODE=dry_run
python 07_storyboard_image/run_staged.py
```

这个模式用于先打通：

```text
06 → 07 → 09
```

也方便 Web UI 展示每一步发生了什么。

---

### 2. execute 真实 ComfyUI 模式

推荐使用 workflow mapping，而不是只靠一套全局 workflow。

```bash
set AI_DRAMA_IMAGE_EXECUTION_MODE=execute
set AI_DRAMA_COMFYUI_BASE_URL=http://127.0.0.1:8188
set AI_DRAMA_COMFYUI_WORKFLOW_MAPPING=D:\path\workflow_mapping.json
python 07_storyboard_image/run_staged.py
```

示例文件：

```text
07_storyboard_image/configs/workflow_mapping.example.json
```

支持四类 workflow：

```text
character_lock          # 文生图定妆照
character_appearance    # 图生图换装造型图
reference_asset         # 场景/道具参考图
storyboard_frame        # 正式单帧分镜图
```

每类 workflow 配置：

```json
{
  "workflow_path": "workflows/storyboard_frame_api.json",
  "positive_node_id": "12",
  "negative_node_id": "13",
  "output_prefix_node_id": "20",
  "positive_input": "text",
  "negative_input": "text",
  "output_prefix_input": "filename_prefix"
}
```

说明：

```text
workflow_path 必须是 ComfyUI 导出的 API 格式 workflow。
07 不强行绑定某套节点包，避免节点名错误导致不可导入。
节点 ID 由 workflow_mapping 指定，便于替换 Flux / SD / IPAdapter / PuLID / InstantID / ControlNet 等方案。
```

---

## 提示词策略

07 使用确定性 prompt_builder，不再依赖 LLM 自动重写 JSON。

默认风格后缀：

```text
Chinese historical drama, cinematic realistic live-action style, natural color, ancient China setting, consistent characters, stable scene, high detail, no modern objects
```

可覆盖：

```bash
set AI_DRAMA_IMAGE_STYLE_SUFFIX=你的统一画风后缀
```

默认负向提示词：

```text
modern objects, modern clothing, western face, cartoon, anime, 3d render, low quality, blurry, extra limbs, deformed hands, wrong gender, duplicate people, text, watermark
```

可覆盖：

```bash
set AI_DRAMA_IMAGE_NEGATIVE_PROMPT=你的负向提示词
```

---

## 局部重跑与依赖图

07 会生成：

```text
dependency_index.json
```

记录：

```text
角色定妆图 → 哪些造型图
角色造型图 → 哪些分镜帧
场景参考图 → 哪些分镜帧
道具参考图 → 哪些分镜帧
每个 frame 的依赖项
```

重跑策略：

```text
定妆图失败：只重跑该角色定妆图，并标记下游造型图 / 分镜帧 stale
造型图失败：只重跑该 appearance_asset_key，并标记关联分镜帧 stale
参考图失败：只重跑该场景或道具图，并标记关联分镜帧 stale
分镜图失败：只重跑失败 frame
```

07E 会输出：

```text
retry_plan
```

---

## Web UI 接入

Web UI 已新增：

```text
图片阶段
```

展示内容：

```text
07A 角色定妆图
07B 角色造型图 / 换装图
07C 场景 / 道具参考图
07D 正式单帧分镜图
07E 依赖图与重跑状态
```

启动：

```bash
python web_ui/server.py --host 127.0.0.1 --port 1144
```

---

## 资源释放规则

07 是图片阶段。入口开始时会调用：

```text
resource_manager.release_llm_resources()
```

也就是说，06 → 07 是本地模型族切换边界：先释放 LLM/Gemma 资源，再进入 ComfyUI 图片阶段。

模块结束时会调用：

```text
resource_manager.release_local_resources("07_storyboard_image")
```

默认只做 Python/CUDA 清理；如果在 `configs/local_resource_release.json` 启用外部命令，也可以执行图片模型释放脚本。

---

## 与其他模块关系

```text
06_storyboard → 07_storyboard_image → 09_video
```

`07_storyboard_image/image_manifest.json` 是 09 视频阶段读取单帧图、四宫格/多图拼接、音频驱动视频生成的基础输入。
