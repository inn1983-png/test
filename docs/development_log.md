# 开发记录与协作规则

本文档只记录关键架构、重要规则、schema 变化和用户明确要求。重复流水账、过细命令、已被 README 覆盖的长篇说明可以删除。

---

# 协作规则

1. 用户给出明确方向后，可以连续修改代码和文档，不需要每个小改动都反复确认。
2. 每轮重要改动后，必须同步更新 README 或 docs。
3. 每轮结束必须总结：做了什么、改了哪些文件、下一步建议。
4. 需要提前确认的情况：删除大量文件、重构核心架构、改变模块边界、修改既定数据目录规则、可能破坏现有可运行流程。

---

# 当前阶段

```text
00 + 01–10 子系统框架已能闭环。
01 小说解析系统已具备真实 LLM 分阶段解析、评分、JSON 修复、总检重跑和 schema 硬校验。
02 剧本改编系统已升级到 schema 1.2，成为音频驱动、单帧分镜友好、多版本评估、失败样本回灌的真实 LLM 子系统。
03/04/05 已从旧 scaffold library 目录切换为真实资产 system：03_character_system、04_scene_system、05_prop_system。
```

---

# 关键架构

## 00 总控

模块运行入口规则：

```text
如果模块目录存在 run_staged.py，00 优先运行 run_staged.py。
否则运行 run.py。
```

当前 pipeline 模块顺序：

```text
01_novel_parser
02_script_writer
03_character_system
04_scene_system
05_prop_system
06_storyboard
07_storyboard_image
08_audio
09_video
10_final_assembly
```

旧 scaffold 目录：

```text
03_character_library
04_scene_library
05_prop_library
```

已不再作为正式 pipeline 模块使用；旧 run.py scaffold 入口已删除。

---

# 01 小说解析系统

正式入口：

```text
01_novel_parser/run_staged.py
```

当前能力：

```text
真实 LLM 分阶段解析
程序锁定段落边界
LLM 标注段落属性
事件图谱生成
长文本分批候选提取
候选批次合并
声音/视频生产预判
JSON 修复
阶段评分与修改意见重跑
01F 总检触发阶段重跑
最终 schema 硬规则校验
测试样例与测试清单
```

01 只做：

```text
理解
解析
故事质量控制
生产预判
```

01 禁止做：

```text
改写小说
扩写剧情
生成正式剧本
生成分镜
生成图像提示词
生成视频提示词
直接写入 shared_assets
```

候选提取最高规则：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
重要性只作为 importance 字段评分，不能作为是否提取的门槛。
候选过多不算错误；遗漏才需要返工。
01 不负责最终筛选、合并、去重。03/04/05 负责标准化。
```

---

# 02 剧本改编系统

正式入口：

```text
02_script_writer/run_staged.py
```

当前能力：

```text
真实 LLM 分阶段剧本改编
02A 改编蓝图 + 长度策略 + 分集/分段计划 + 多版本策略
02B 剧本结构 + 角色称呼一致性 + 连续性种子 + 情绪曲线
02C 语音行预拆分 + 6-12 秒视频单元候选
02D 多版本正式剧本 + 最终版本选择 + 原文关键句继承 + 口播节奏检查
02E 剧本生产标注 + 单帧分镜准备字段 + 画面可执行性 + 人物负载 + 连续性链表
02F 总检评分 + 失败样本回灌建议
JSON 修复
阶段评分与修改意见重跑
02F 总检触发阶段重跑
最终 schema 硬规则校验
script.json / script.txt / script_meta.json 输出
```

02 只做：

```text
剧本改编
对白 / OS / 留白 / 动作 / 情绪
N/D/M/S 语音行预拆分
分集/分段计划
多版本剧本生成与选择
原文关键句继承
口播节奏检查
剧本层面的音频提示
剧本层面的单帧分镜动作链和连续性提示
画面可执行性检查
角色上场人数负载检查
失败样本回灌建议
剧本质量评分和修改意见
```

02 禁止做：

```text
角色资产标准化
场景资产标准化
道具资产标准化
正式分镜生成
图像提示词生成
视频提示词生成
ComfyUI 调用
直接写入 shared_assets
```

02 单帧分镜路线：

```text
单帧 = 生产单位
四宫格 = 后续连续性预览 / 检查单位
02 只输出 visual_dramatic_units / storyboard_hints / continuity_chain 等剧本层动作链和连续性提示。
```

---

# 03 角色库系统

正式入口：

```text
03_character_system/run_staged.py
```

核心文件：

```text
03_character_system/core/llm_client.py
03_character_system/core/json_repair.py
03_character_system/core/quality_checker.py
03_character_system/core/schema_validator.py
03_character_system/core/stage_runner.py
```

阶段提示词：

```text
03_character_system/prompts/03A_alias_merge_plan.md
03_character_system/prompts/03B_character_cards.md
03_character_system/prompts/03C_script_usage_binding.md
03_character_system/prompts/03D_quality_check.md
```

输入：

```text
01: candidate_characters / paragraphs / events / character_arc_map
02: segments / character_name_usage / visual_dramatic_units / storyboard_hints / continuity_chain
```

输出：

```text
03_character_system/characters.json
03_character_system/character_meta.json
```

03 只做：

```text
角色资产标准化
角色别名合并
角色卡稳定化
角色剧本使用绑定
证据链
角色连续性注意事项
```

03 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
场景资产标准化
道具资产标准化
ComfyUI 调用
```

03 阶段：

```text
03A alias_merge_plan
03B character_cards
03C script_usage_binding
03D quality_check
```

03 最高规则：

```text
合并同一角色的不同称呼。
禁止按年龄段拆角色。
禁止把身份称谓、昵称、职务称谓拆成新角色。
输出 canonical_name、aliases、gender、age_range、identity、appearance、costume、temperament、role_function、source_evidence、usage_in_script。
角色描述必须稳定、清晰、不可互相污染，服务 06 单帧分镜引用稳定角色名。
```

---

# 04 场景库系统

正式入口：

```text
04_scene_system/run_staged.py
```

核心文件：

```text
04_scene_system/core/llm_client.py
04_scene_system/core/json_repair.py
04_scene_system/core/quality_checker.py
04_scene_system/core/schema_validator.py
04_scene_system/core/stage_runner.py
```

阶段提示词：

```text
04_scene_system/prompts/04A_scene_merge_plan.md
04_scene_system/prompts/04B_scene_cards.md
04_scene_system/prompts/04C_script_usage_binding.md
04_scene_system/prompts/04D_quality_check.md
```

输入：

```text
01: candidate_scenes / paragraphs / events / scene_value_map
02: scene_beats / visual_dramatic_units / storyboard_hints / segments / continuity_chain
```

输出：

```text
04_scene_system/scenes.json
04_scene_system/scene_meta.json
```

04 只做：

```text
场景资产标准化
场景别名合并
主场景/子场景/临时地点区分
场景剧本使用绑定
证据链
场景连续性规则
```

04 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
角色资产标准化
道具资产标准化
ComfyUI 调用
```

04 阶段：

```text
04A scene_merge_plan
04B scene_cards
04C script_usage_binding
04D quality_check
```

04 最高规则：

```text
合并同一场景的不同说法。
区分主场景、子场景、临时地点。
输出 canonical_scene_name、aliases、scene_type、time_period、lighting、weather、atmosphere、layout、key_visual_elements、continuity_rules、source_evidence、usage_in_script。
场景描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
```

---

# 05 道具库系统

正式入口：

```text
05_prop_system/run_staged.py
```

核心文件：

```text
05_prop_system/core/llm_client.py
05_prop_system/core/json_repair.py
05_prop_system/core/quality_checker.py
05_prop_system/core/schema_validator.py
05_prop_system/core/stage_runner.py
```

阶段提示词：

```text
05_prop_system/prompts/05A_prop_merge_plan.md
05_prop_system/prompts/05B_prop_cards.md
05_prop_system/prompts/05C_script_usage_binding.md
05_prop_system/prompts/05D_quality_check.md
```

输入：

```text
01: candidate_props / paragraphs / events / asset_binding_hints
02: segments / visual_dramatic_units / storyboard_hints / scene_beats / continuity_chain
```

输出：

```text
05_prop_system/props.json
05_prop_system/prop_meta.json
```

05 只做：

```text
道具资产标准化
道具别名合并
关键道具/普通道具/背景物件区分
道具剧本使用绑定
证据链
道具连续性注意事项
```

05 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
角色资产标准化
场景资产标准化
ComfyUI 调用
```

05 阶段：

```text
05A prop_merge_plan
05B prop_cards
05C script_usage_binding
05D quality_check
```

05 最高规则：

```text
合并同一道具的不同说法。
区分关键道具、普通道具、背景物件。
输出 canonical_prop_name、aliases、prop_type、owner_character、usage_function、appearance、material、risk_notes、source_evidence、usage_in_script。
道具描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
```

---

# 03/04/05 共同真实执行机制

## 真实 LLM

03/04/05 不支持正式流程使用 scaffold 占位结果。必须配置：

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

## 阶段评分与修改意见重跑

```text
每阶段生成后 quality_checker.py 评分。
低于阈值时生成 revision_instructions，并把修改意见传回同阶段 LLM 自动重跑。
```

## 总检连锁重跑

```text
03D / 04D / 05D 输出 needs_retry=true 和 retry_stages 时，stage_runner.py 会从最早问题阶段开始，连同后续阶段再跑一轮。
```

示例：

```text
03D 发现角色一开始就合并错了 → retry_stages = ["03A"]
系统会重跑：03A → 03B → 03C → 03D
```

## JSON 修复机制

```text
LLM 返回 JSON 解析失败时，json_repair.py 会把 broken_json 和错误原因发回 LLM。
该机制只修复 JSON 格式，不新增业务内容。
```

## 最终 schema 硬规则校验

```text
03 schema_validator.py 检查角色字段完整、别名冲突、年龄段误拆、证据链和剧本使用绑定。
04 schema_validator.py 检查场景字段完整、别名冲突、越界 prompt 字段、证据链和剧本使用绑定。
05 schema_validator.py 检查道具字段完整、别名冲突、越界 prompt 字段、证据链和剧本使用绑定。
```

---

# 下一步建议测试顺序

准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

配置本地 LLM：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

建议依次测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 03_character_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 04_scene_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 05_prop_system
```

完整测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

---

# 用户最新明确要求

```text
03/04/05 必须是真实可用子系统，不要 scaffold 占位。
必须采用分阶段真实 LLM 调用。
每个阶段都要有评分。
评分不合格要生成修改意见。
修改意见要能传回 LLM 自动重跑。
总检阶段要能触发从最早问题阶段开始连锁重跑。
必须有 JSON 修复机制。
必须有最终 schema 硬规则校验。
每个系统都要有 run_staged.py。
每个系统都要写 README。
必须更新 docs/development_log.md。
03/04/05 形成稳定资产库，让 06 单帧分镜可以直接引用稳定角色名、稳定场景名、稳定道具名，避免角色串脸、场景漂移、道具混乱。
```
