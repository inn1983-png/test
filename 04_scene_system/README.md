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
04 = 先合并，再分级，再复核，不简单删除候选
06 = 只引用 04 输出的稳定场景名和主场景/子场景关系
```

## 资产分级

04B 必须给每个场景输出：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis
asset_level = main_scene / sub_scene / temporary / background
needs_reference_image = true / false
parent_scene
reference_image_plan
```

分级必须参考 01 的真正理解：

```text
story_understanding
story_spine
events / event_graph
conflicts
high_retention_segments
scene_value_map
visual_risk_report
paragraphs
```

## 复核机制

04E 是面向 06 的资产可用性复核，不是格式检查。

04E 必须检查：

```text
是否把同一场景拆太碎
是否把不同场景错误合并
主场景 / 子场景 / 临时地点分级是否合理
子场景是否正确绑定 parent_scene
主场景是否有全景图计划
临时地点是否误升为主场景
背景物件是否错误变成场景
06 是否能直接引用 canonical_scene_name
```

04E 输出：

```text
asset_review_report
downstream_readiness_for_06
main_assets_for_06
optional_assets_for_06
do_not_reference_as_main_asset
upstream_blocking_issues
```

如果 04E 发现遗漏或误分级，不直接补资产，而是输出 retry_stages 和 revision_instructions，触发前置阶段连锁重跑。

## 参考图策略

```text
main_scene：wide_establishing_view，先用全景图稳定空间。
sub_scene：需要时再补 local_area_view。
temporary / background：只保留文字资产，不强制做图。
```

最高图像资产规则：

```text
04 不生成图片，只写参考图计划。
场景优先全景图，不要一开始做大量多角度。
先主场景全景，再根据 06/07 失败情况补子区域局部图。
图片由 07 根据 06 实际分镜需求统一生成。
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
面向 06 的资产复核
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
04B scene_cards：输出稳定场景卡 + 资产分级 + 重要性评分
04C script_usage_binding：绑定 02 剧本里的场景使用
04D quality_check：模块内部总检评分
04E asset_review：基于 01 真正理解，面向 06 复核资产可用性
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成 `revision_instructions`，并把修改意见传回同阶段 LLM 自动重跑。

04D / 04E 如果输出 `needs_retry=true`，系统会从最早问题阶段开始连锁重跑：

```text
04A → 04B → 04C → 04D → 04E
```

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
scenes 是否为空
scene_id 是否重复
canonical_scene_name 是否重复
aliases 是否互相冲突
asset_importance_score 是否为 0-100
source_understanding_basis 是否引用 01 理解依据
asset_level 是否合法
主场景是否 needs_reference_image=true
主场景 reference_image_plan 是否包含 wide_establishing_view
子场景是否绑定 parent_scene
asset_review_report 是否存在
downstream_readiness_for_06 是否存在
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
asset_importance_score
importance_reason
source_understanding_basis
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
