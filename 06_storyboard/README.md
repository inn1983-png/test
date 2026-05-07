# 06 单帧分镜系统

## 模块定位

06_storyboard 负责把 02 剧本与 03/04/05 稳定资产库转成正式单帧分镜 JSON。

它读取：

```text
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
```

它输出：

```text
06_storyboard/storyboard.json
06_storyboard/storyboard_meta.json
```

---

## 最高边界

06 只做：

```text
单帧分镜拆分
剧本片段到分镜帧的覆盖映射
稳定角色 / 场景 / 道具引用
reference_requirements
composition_notes
continuity_notes
四宫格连续性预览组
07 图片生成前的分镜质量总检
```

06 禁止做：

```text
生成图片
调用 ComfyUI
生成最终视频
生成图像提示词
生成视频提示词
输出 prompt / image_prompt / desc_prompt / desc_promopt / negative_prompt / video_prompt 字段
新增 03/04/05 不存在的主角色、主场景、关键道具
```

---

## 资产引用规则

06 的分镜必须严格引用 03/04/05 的稳定资产名：

```text
角色：03_character_system.characters[].canonical_name
场景：04_scene_system.scenes[].canonical_scene_name
道具：05_prop_system.props[].canonical_prop_name
```

如果 02 剧本需要的角色、场景、道具不在资产库里，06 不能自己硬补。

必须输出：

```text
upstream_blocking_issues
```

并建议对应上游模块阶段重跑：

```text
03_character_system：03B / 03E
04_scene_system：04B / 04E
05_prop_system：05B / 05E
```

---

## 分阶段真实 LLM 流程

正式入口：

```bash
python 06_storyboard/run_staged.py
```

阶段：

```text
06A asset_gate：资产闸门检查，只生成 allowed_asset_names 和 upstream_blocking_issues
06B storyboard_plan：规划单帧分镜组、帧数密度、覆盖范围和连续性策略
06C single_frame_storyboard：生成正式 frames 单帧分镜 JSON
06D continuity_binding：生成 continuity_map 和 four_grid_preview_groups
06E quality_check：总检资产引用、剧情覆盖、连续性、07 可用性和越界字段
```

每个阶段都真实调用本地 LLM，阶段后进入 `quality_checker.py` 评分。

评分低于阈值会生成 `revision_instructions`，传回同阶段 LLM 自动重跑。

06D / 06E 如果输出 `needs_retry=true` 和 `retry_stages`，`stage_runner.py` 会从最早问题阶段开始连锁重跑。

---

## JSON 修复与本地 Gemma 适配

06 使用：

```text
06_storyboard/core/llm_client.py
06_storyboard/core/json_repair.py
00_common/llm_prompt_guard.py
```

适配本地 Gemma 4 31B Q4：

```text
默认 temperature = 0.1
强制只输出 JSON object
禁止 Markdown / 前言 / 后记
parse_json_from_text 后递归 remove_internal_output_fields
repair fallback 后再次 remove_internal_output_fields
```

如果未配置本地 LLM，06 会直接失败，不生成占位 storyboard.json。

必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选：

```bash
set AI_DRAMA_LLM_API_KEY=你的 key
set AI_DRAMA_LLM_TIMEOUT_SEC=240
set AI_DRAMA_LLM_TEMPERATURE=0.1
```

---

## 输出结构

`storyboard.json` 顶层核心字段：

```json
{
  "schema_version": "1.2",
  "module": "06_storyboard",
  "status": "success / needs_review",
  "stage_mode": "llm",
  "allowed_asset_names": {},
  "asset_availability_report": {},
  "upstream_blocking_issues": [],
  "storyboard_plan": {},
  "frame_group_plan": [],
  "coverage_plan": [],
  "frames": [],
  "continuity_map": [],
  "four_grid_preview_groups": [],
  "reference_requirements_summary": {},
  "quality_report": {},
  "schema_validation": {}
}
```

每个 frame 必须包含：

```text
frame_id
sequence_index
source_segment_ids
source_voice_line_ids
source_visual_unit_ids
scene.canonical_scene_name
characters[].canonical_name
props[].canonical_prop_name
story_action
emotion
camera_plan
reference_requirements
composition_notes
continuity_notes
next_frame_link
```

---

## 四宫格说明

06 的四宫格不是一次性生成四宫格图片。

它只输出：

```text
four_grid_preview_groups
```

用于后续检查连续性，例如：

```text
1-4
4-7
7-10
```

上一组末帧可以作为下一组首帧，帮助 07/09 稳定连续画面。

---

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
frames 是否为空
frame_id / sequence_index 是否重复
sequence_index 是否从 1 连续递增
每帧是否有必要字段
每帧角色是否来自 allowed_asset_names.characters
每帧场景是否来自 allowed_asset_names.scenes
每帧道具是否来自 allowed_asset_names.props
allowed_asset_names 是否真实来自 03/04/05 资产库
是否出现 prompt / image_prompt / desc_prompt / desc_promopt / video_prompt 等越界字段
资产不可用时是否输出 upstream_blocking_issues
```

---

## 与上下游关系

```text
02_script_writer + 03_character_system + 04_scene_system + 05_prop_system
  ↓
06_storyboard
  ↓
07_storyboard_image
```

06 为 07 提供的是结构化分镜需求，不是绘图提示词。

07 可以基于：

```text
reference_requirements
composition_notes
continuity_notes
stable asset names
```

继续生成图像提示词和图片。

---

## 显存释放

06 属于 LLM_TEXT_PHASE。

运行结束后可以调用：

```python
resource_manager.release_local_resources("06_storyboard")
```

但根据 00 的阶段规则，01–06 不主动卸载 LLM，只做轻量清理。

真正释放 LLM 显存发生在：

```text
06_storyboard -> 07_storyboard_image
```

由 00_main_controller/run_pipeline.py 统一调用 `release_llm_resources()`。

---

## 测试建议

先完成 01–05 后只跑 06：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 06_storyboard
```

完整跑到 06：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

先校验 pipeline：

```bash
python 00_main_controller/validate_pipeline.py --pipeline pipeline.json --strict-order
```
