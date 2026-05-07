# 04 场景库系统

## 模块定位

04_scene_system 只负责场景资产标准化。

它读取：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
```

核心原则：

```text
01 = 提取一切，宁可多提，不漏掉
04 = 先合并，再分级，不简单删除候选
06 = 只引用 04 输出的稳定场景名和主场景/子场景关系
```

## 资产分级

04B 必须给每个场景输出：

```text
asset_level = main_scene / sub_scene / temporary / background
needs_reference_image = true / false
parent_scene
reference_image_plan
```

分级规则：

```text
main_scene：主场景，反复出现或承载核心戏，必须有全景参考图。
sub_scene：主场景的一部分，如门口、桌前、堂下，必须绑定 parent_scene。
temporary：临时地点，一般不生成参考图。
background：背景地点或泛称地点，一般不生成参考图。
```

参考图策略：

```text
main_scene：wide_establishing_view，先用全景图稳定空间。
sub_scene：需要时再补 local_area_view。
temporary / background：只保留文字资产，不强制做图。
```

最高图像资产规则：

```text
场景优先全景图，不要一开始做大量多角度。
先主场景全景，再根据 06/07 失败情况补子区域局部图。
场景系统只写资产描述和参考图计划，不写图像提示词。
```

## 绝对边界

04 只做：

```text
场景合并
场景别名归并
主场景/子场景/临时地点区分
场景资产分级
稳定场景卡
剧本使用绑定
证据链
场景连续性规则
场景库质量评分
```

04 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
ComfyUI 调用
角色资产标准化
道具资产标准化
```

## 分阶段真实 LLM 流程

正式入口：

```bash
python 04_scene_system/run_staged.py
```

阶段：

```text
04A scene_merge_plan：合并同一场景的不同说法
04B scene_cards：输出稳定场景卡 + 资产分级
04C script_usage_binding：绑定 02 剧本里的场景使用
04D quality_check：总检评分，可触发连锁重跑
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成 `revision_instructions`，并把修改意见传回同阶段 LLM 自动重跑。

04D 如果输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["04A"]
  }
}
```

系统会从最早问题阶段开始连锁重跑：

```text
04A → 04B → 04C → 04D
```

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
scenes 是否为空
scene_id 是否重复
canonical_scene_name 是否重复
aliases 是否互相冲突
asset_level 是否合法
主场景是否 needs_reference_image=true
主场景 reference_image_plan 是否包含 wide_establishing_view
子场景是否绑定 parent_scene
是否出现 prompt / image_prompt / desc_prompt 等越界字段
source_evidence 是否存在
usage_in_script 是否为数组
```

## 核心输出字段

每个场景必须包含：

```text
canonical_scene_name
aliases
scene_type
asset_level
needs_reference_image
parent_scene
reference_image_plan
time_period
lighting
weather
atmosphere
layout
key_visual_elements
continuity_rules
source_evidence
usage_in_script
```

## 最高规则

```text
合并同一场景的不同说法。
区分主场景、子场景、临时地点。
场景描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
```

## LLM 配置

必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选：

```bash
set AI_DRAMA_LLM_API_KEY=你的 key
set AI_DRAMA_LLM_TIMEOUT_SEC=180
set AI_DRAMA_LLM_TEMPERATURE=0.2
```
