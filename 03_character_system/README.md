# 03 角色库系统

## 模块定位

03_character_system 只负责角色资产标准化。

它读取：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
```

核心原则：

```text
01 = 提取一切，宁可多提，不漏掉
03 = 先合并，再分级，再复核，不简单删除候选
03 = 为主/配角建立稳定角色卡、定妆照需求、服装版本 costume_variants
06 = 只引用 03 输出的 canonical_name + costume_id，不新增角色或服装版本
07 = 后续先用 03 定妆照锁脸，再基于定妆照图生图换装生成角色造型照
```

## 资产分级

03B 必须给每个角色输出：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis
asset_level = main / supporting / extra_group / mentioned_only
needs_fixed_face = true / false
reference_image_priority = required / optional / not_needed
reference_image_plan
default_costume_id
costume_variants
```

分级必须参考 01 的真正理解：

```text
story_understanding
story_spine
events / event_graph
conflicts
high_retention_segments
character_arc_map
paragraphs
```

## 定妆照与服装版本策略

为了保证角色一致性，03 采用：

```text
先定妆照锁脸 → 再图生图换装生成造型照 → 正式分镜图引用造型照
```

03 不生成图片，但必须为 07 预留清晰需求：

```text
character_lock_reference：未来 07 用于生成/引用角色定妆照，锁脸、年龄、基础发型、身形、气质。
costume_variants：角色不同剧情阶段的完整服装状态。
default_costume_id：默认服装版本，必须存在于 costume_variants。
integrated_wearable_props：可并入造型照的常驻穿戴物。
```

main / supporting 角色必须至少有一个 `costume_variants`，且只能有一个 `is_default=true`。

服装变化不能拆成新角色：

```text
张捕头 + 官服
张捕头 + 便服
张捕头 + 夜行衣
```

都必须是同一个 `canonical_name` 下的不同 `costume_id`。

## 复核机制

03E 是面向 06 的资产可用性复核，不是格式检查。

03E 必须检查：

```text
是否漏掉主角/反派/关键配角
是否把同一角色拆成多个
是否把不同角色错误合并
是否按年龄段/称谓/职务拆角色
是否把龙套误升为主资产
asset_level / fixed face / reference plan 是否合理
main/supporting 是否缺 default_costume_id / costume_variants
02 出现换装、伪装、婚服、夜行服、破损衣服、孝服等阶段时是否有对应 costume_variant
06 是否能直接引用 canonical_name + costume_id
```

03E 输出：

```text
asset_review_report
downstream_readiness_for_06
main_assets_for_06
optional_assets_for_06
do_not_reference_as_main_asset
upstream_blocking_issues
```

如果 03E 发现遗漏、误分级或缺少服装版本，不直接补资产，而是输出 retry_stages 和 revision_instructions，触发前置阶段连锁重跑。

## 参考图策略

```text
main：front_face_half_body + full_body_front，用于定妆照锁脸
supporting：front_face_half_body，用于定妆照锁脸
costume_variants：后续 07 基于定妆照图生图换装生成角色造型照
extra_group / mentioned_only：不强制参考图
```

最高图像资产规则：

```text
03 不生成图片，只写参考图计划和服装版本计划。
先单视图定妆照稳定，不要一开始做三视图。
不要把正面/侧面/背面拼成一张三视图图板。
如后续确实需要三视图，必须拆成 front / side / back 多张独立图。
图片由 07 根据 06 实际分镜需求统一生成。
```

## 绝对边界

03 只做：

```text
角色合并
角色别名归并
角色资产分级
稳定角色卡
定妆照需求
服装版本 costume_variants
剧本使用绑定
证据链
角色连续性规则
角色库质量评分
面向 06 的资产复核
```

03 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
ComfyUI 调用
场景资产标准化
道具资产标准化
```

## 分阶段真实 LLM 流程

正式入口：

```bash
python 03_character_system/run_staged.py
```

阶段：

```text
03A alias_merge_plan：合并同一角色的不同称呼
03B character_cards：输出稳定角色卡 + 资产分级 + 重要性评分 + costume_variants
03C script_usage_binding：绑定 02 剧本里的角色使用与 costume_id 使用
03D quality_check：模块内部总检评分
03E asset_review：基于 01 真正理解，面向 06 复核角色与服装版本可用性
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成 `revision_instructions`，并把修改意见传回同阶段 LLM 自动重跑。

03D / 03E 如果输出 `needs_retry=true`，系统会从最早问题阶段开始连锁重跑：

```text
03A → 03B → 03C → 03D → 03E
```

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
characters 是否为空
character_id 是否重复
canonical_name 是否重复
aliases 是否互相冲突
是否按年龄段拆角色
asset_importance_score 是否为 0-100
source_understanding_basis 是否引用 01 理解依据
asset_level 是否合法
主/配角是否 needs_fixed_face=true
龙套/仅提及角色是否错误强制参考图
核心角色 reference_image_plan 是否包含 front_face_half_body
main/supporting 是否包含 default_costume_id / costume_variants
默认 costume_id 是否真实存在于 costume_variants
costume_variants 是否且仅有一个 is_default=true
asset_review_report 是否存在
downstream_readiness_for_06 是否存在
source_evidence 是否存在
usage_in_script 是否为数组
```

## 核心输出字段

每个角色必须包含：

```text
canonical_name
aliases
gender
age_range
identity
appearance
costume
default_costume_id
costume_variants
temperament
role_function
asset_importance_score
importance_reason
source_understanding_basis
asset_level
needs_fixed_face
reference_image_priority
reference_image_plan
source_evidence
usage_in_script
anti_contamination_notes
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
