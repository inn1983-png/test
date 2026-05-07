# 07 分镜图生成系统

## 模块定位

`07_storyboard_image` 是图片执行阶段，负责把 `06_storyboard/storyboard.json` 中的单帧分镜、角色造型引用、场景引用、道具引用，转成可执行图片任务，并输出 `image_manifest.json`。

它不重新写剧情、不重新规划分镜、不新增角色/场景/道具资产。它只做三件事：

```text
读取 06 单帧分镜
构建参考图任务 + 正式分镜图任务
调用本地 ComfyUI 或 dry_run 生成图片清单
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

可选输入，用于记录 schema 版本与后续扩展资产核对：

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

关键产物：

```text
07_storyboard_image/image_manifest.json
07_storyboard_image/image_meta.json
07_storyboard_image/intermediate/07A_reference_asset_prepare.json
07_storyboard_image/intermediate/07B_frame_image_tasks.json
07_storyboard_image/intermediate/07C_comfyui_execution.json
07_storyboard_image/intermediate/07D_manifest_quality_check.json
07_storyboard_image/images/shot_001.png
07_storyboard_image/images/shot_002.png
...
```

`image_manifest.json` 会包含：

```text
reference_asset_tasks      # 角色造型照、场景图、道具图任务
frame_image_tasks          # 每一帧的正式图片生成任务
execution_results          # dry_run / ComfyUI 执行结果
images                     # 每个 frame_id 对应的图片路径和引用资产
missing_references         # 严格模式下缺失的参考图
quality_report             # 是否需要重跑、失败帧、schema 校验结果
```

---

## 阶段设计

```text
07A reference_asset_prepare
    收集 06 appearance_asset_requirements、场景、道具，生成参考资产任务。

07B frame_image_task_build
    把每个 06 frame 转成图片任务，生成 positive_prompt / negative_prompt / reference_images / output_basename。

07C comfyui_execution
    默认 dry_run，只写 planned 结果；execute 模式下提交 ComfyUI workflow。

07D manifest_quality_check
    汇总 image_manifest，检查失败帧，生成 retry_plan。
```

---

## 执行模式

### 1. dry_run 默认模式

不调用 ComfyUI，只生成任务清单和计划图片路径。

```bash
set AI_DRAMA_IMAGE_EXECUTION_MODE=dry_run
python 07_storyboard_image/run_staged.py
```

这个模式用于先打通 06 → 07 → 09 的数据结构，也方便 Web UI 展示每一步发生了什么。

### 2. execute 真实 ComfyUI 模式

```bash
set AI_DRAMA_IMAGE_EXECUTION_MODE=execute
set AI_DRAMA_COMFYUI_BASE_URL=http://127.0.0.1:8188
set AI_DRAMA_COMFYUI_WORKFLOW=D:\path\to\workflow_api.json
set AI_DRAMA_COMFYUI_POSITIVE_NODE_ID=12
set AI_DRAMA_COMFYUI_NEGATIVE_NODE_ID=13
set AI_DRAMA_COMFYUI_OUTPUT_PREFIX_NODE_ID=20
python 07_storyboard_image/run_staged.py
```

可选注入字段名：

```bash
set AI_DRAMA_COMFYUI_POSITIVE_INPUT=text
set AI_DRAMA_COMFYUI_NEGATIVE_INPUT=text
set AI_DRAMA_COMFYUI_OUTPUT_PREFIX_INPUT=filename_prefix
```

说明：

```text
workflow_api.json 必须是 ComfyUI 导出的 API 格式 workflow。
07 不强行绑定某套节点包，避免节点名错误导致不可导入。
节点 ID 由环境变量指定，便于替换 Flux / SD / IPAdapter / PuLID / InstantID / ControlNet 等方案。
```

---

## 参考图路径规则

默认参考图基准目录：

```text
shared_assets
```

可通过环境变量覆盖：

```bash
set AI_DRAMA_ASSET_IMAGE_BASE=workspace/books/book_001/shared_assets
```

默认推导路径：

```text
shared_assets/characters/appearance/{appearance_asset_key}.png
shared_assets/scenes/{canonical_scene_name}.png
shared_assets/props/{canonical_prop_name}.png
```

严格检查参考图是否存在：

```bash
set AI_DRAMA_REQUIRE_REFERENCE_IMAGES=1
```

不开严格检查时，07 只记录 expected image path，不因为参考图文件暂时不存在而中断。

---

## 提示词策略

07 会把 06 的结构化字段转成图片执行提示：

```text
story_action
emotion
camera_plan
composition_notes
continuity_notes
scene / characters / props 引用
```

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

`07_storyboard_image` 输出的 `image_manifest.json` 是 09 视频阶段读取单帧图、四宫格/多图拼接、音频驱动视频生成的基础输入。
