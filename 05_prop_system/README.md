# 05 道具库系统

## 模块定位

05_prop_system 只负责道具资产标准化。

它读取：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
```

核心原则：

```text
01 = 提取一切，宁可多提，不漏掉
05 = 先合并，再分级，再复核，不简单删除候选
06 = 只引用 05 输出的稳定道具名和关键/动作道具
```

## 资产分级

05B 必须给每个道具输出：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis
asset_level = key_prop / action_prop / background_object / mentioned_only
needs_reference_image = true / false
reference_image_plan
```

分级必须参考 01 的真正理解：

```text
story_understanding
story_spine
events / event_graph
conflicts
high_retention_segments
asset_binding_hints
visual_risk_report
paragraphs
```

## 复核机制

05E 是面向 06 的资产可用性复核，不是格式检查。

05E 必须检查：

```text
是否漏掉关键道具
是否把背景物件误升为关键道具
是否把同一道具拆成多个
关键道具是否必须做 clean_front_view
普通道具是否被过度资产化
背景物件是否归入场景元素
owner_character 是否合理
06 是否能直接引用 canonical_prop_name
```

05E 输出：

```text
asset_review_report
downstream_readiness_for_06
main_assets_for_06
optional_assets_for_06
do_not_reference_as_main_asset
upstream_blocking_issues
```

如果 05E 发现遗漏或误分级，不直接补资产，而是输出 retry_stages 和 revision_instructions，触发前置阶段连锁重跑。

## 参考图策略

```text
key_prop：clean_front_view；复杂道具可加 side_view。
action_prop：需要时再做 clean_front_view。
background_object / mentioned_only：不强制做图，尽量归入场景元素。
```

最高图像资产规则：

```text
05 不生成图片，只写参考图计划。
关键道具用单独干净图。
普通道具和背景物件不要全部做图，否则资产库会爆炸。
道具图不要和角色/场景混在一起。
图片由 07 根据 06 实际分镜需求统一生成。
```

## 绝对边界

05 只做：

```text
道具合并
道具别名归并
关键道具/动作道具/背景物件区分
道具资产分级
稳定道具卡
剧本使用绑定
证据链
道具连续性规则
道具库质量评分
面向 06 的资产复核
```

05 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
ComfyUI 调用
角色资产标准化
场景资产标准化
```

## 分阶段真实 LLM 流程

正式入口：

```bash
python 05_prop_system/run_staged.py
```

阶段：

```text
05A prop_merge_plan：合并同一道具的不同说法
05B prop_cards：输出稳定道具卡 + 资产分级 + 重要性评分
05C script_usage_binding：绑定 02 剧本里的道具使用
05D quality_check：模块内部总检评分
05E asset_review：基于 01 真正理解，面向 06 复核资产可用性
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成 `revision_instructions`，并把修改意见传回同阶段 LLM 自动重跑。

05D / 05E 如果输出 `needs_retry=true`，系统会从最早问题阶段开始连锁重跑：

```text
05A → 05B → 05C → 05D → 05E
```

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
props 是否为空
prop_id 是否重复
canonical_prop_name 是否重复
aliases 是否互相冲突
asset_importance_score 是否为 0-100
source_understanding_basis 是否引用 01 理解依据
asset_level 是否合法
关键道具是否 needs_reference_image=true
关键道具 reference_image_plan 是否包含 clean_front_view
asset_review_report 是否存在
downstream_readiness_for_06 是否存在
是否出现 prompt / image_prompt / desc_prompt 等越界字段
source_evidence 是否存在
usage_in_script 是否为数组
```

## 核心输出字段

每个道具必须包含：

```text
canonical_prop_name
aliases
prop_type
asset_importance_score
importance_reason
source_understanding_basis
asset_level
needs_reference_image
reference_image_plan
owner_character
usage_function
appearance
material
risk_notes
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
