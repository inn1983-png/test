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

当前阶段：

```text
00 + 01–10 子系统框架已能闭环。
01 理论搭建已完成，进入等待统一测试阶段。
02 剧本改编系统已完成理论搭建，延续 01 的分阶段真实 LLM + 评分 + 修改意见重跑机制。
```

01 当前能力：

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

02 当前能力：

```text
真实 LLM 分阶段剧本改编
02A 改编蓝图
02B 剧本结构
02C 正式剧本
02D 剧本生产标注
02E 总检评分
JSON 修复
阶段评分与修改意见重跑
02E 总检触发阶段重跑
最终 schema 硬规则校验
script.json / script.txt / script_meta.json 输出
```

---

# 关键架构

## 00 总控

模块运行入口规则：

```text
如果模块目录存在 run_staged.py，00 优先运行 run_staged.py。
否则运行 run.py。
```

## 01 小说解析系统

正式入口：

```text
01_novel_parser/run_staged.py
```

核心文件：

```text
01_novel_parser/core/llm_client.py
01_novel_parser/core/json_repair.py
01_novel_parser/core/paragraph_splitter.py
01_novel_parser/core/chunk_manager.py
01_novel_parser/core/quality_checker.py
01_novel_parser/core/schema_validator.py
01_novel_parser/core/stage_runner.py
```

阶段提示词：

```text
01_novel_parser/prompts/01A_story_understanding.md
01_novel_parser/prompts/01B_paragraph_split.md
01_novel_parser/prompts/01C_event_graph.md
01_novel_parser/prompts/01D_candidate_extract.md
01_novel_parser/prompts/01E_production_predict.md
01_novel_parser/prompts/01F_quality_check.md
```

测试资料：

```text
01_novel_parser/input/novel.txt.example
01_novel_parser/tests/README.md
```

## 02 剧本改编系统

正式入口：

```text
02_script_writer/run_staged.py
```

核心文件：

```text
02_script_writer/core/llm_client.py
02_script_writer/core/json_repair.py
02_script_writer/core/quality_checker.py
02_script_writer/core/schema_validator.py
02_script_writer/core/stage_runner.py
```

阶段提示词：

```text
02_script_writer/prompts/02A_adaptation_blueprint.md
02_script_writer/prompts/02B_script_structure.md
02_script_writer/prompts/02C_script_draft.md
02_script_writer/prompts/02D_production_annotations.md
02_script_writer/prompts/02E_quality_check.md
```

关键输出：

```text
02_script_writer/script.json
02_script_writer/script.txt
02_script_writer/script_meta.json
```

---

# 01 核心原则

schema：

```text
schema_version = 1.2
```

01 最高任务：

```text
先通读全文，理解故事到底讲什么，再做结构解析。
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

故事质量字段：

```text
story_understanding
story_spine
viewer_experience_plan
information_reveal_plan
character_arc_map
scene_value_map
golden_lines
confusion_risk_report
adaptation_strategy
```

生产预判字段：

```text
voice_line_candidates
video_unit_candidates
emotion_curve
asset_binding_hints
visual_risk_report
evidence_index
quality_report
```

---

# 02 核心原则

schema：

```text
schema_version = 1.0
```

02 最高任务：

```text
把 01 的小说解析结果改编成正式剧本，重点是对白 + OS + 留白 + 动作 + 情绪。
```

02 只做：

```text
剧本改编
对白 / OS / 留白 / 动作 / 情绪
剧本层面的音频提示
剧本层面的画面动作锚点
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

02D 边界说明：

```text
02D 的 storyboard_hints 只是剧本层面的画面动作锚点，方便 06 分镜系统使用。
它不是正式分镜，也不是图像提示词。
```

02 反过度压缩规则：

```text
不得把多个关键事件压成一句话。
不得只用 OS 概括冲突。
原文信息量较大时，宁可增加剧本段落，也不能强行压成 2 分钟。
02E 必须检查是否压缩过狠，并可触发 02B 或 02C 重跑。
```

---

# 01 真实执行机制

## 真实 LLM

01 不支持占位解析。必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

## 分阶段

```text
01A 全文理解
01B 段落切分标注
01C 事件图谱
01D 全量候选提取
01E 声音和视频生产预判
01F 汇总校验
```

## 段落稳定

01B 采用：

```text
paragraph_splitter.py 程序锁定 paragraph_id / text / start_char / end_char
LLM 只补充章节、段落类型、timeline 和属性标注
```

## 候选分批

01D 采用：

```text
chunk_manager.py 按段落分批
每批调用 LLM 提取候选
程序合并所有批次
不删除不确定重复项
```

## JSON 修复

LLM 返回 JSON 解析失败时：

```text
json_repair.py 把 broken_json 和错误原因发回 LLM
要求只修复 JSON 格式
```

## 评分与重跑

```text
每阶段生成后 quality_checker.py 评分。
低于阈值时生成 revision_instructions，并把修改意见传回同阶段重跑。
01F 总检如果输出 needs_retry=true 和 retry_stages，会从最早有问题的阶段开始，连同后续阶段再跑一轮。
```

## 硬规则校验

最终合并后 `schema_validator.py` 检查：

```text
必要顶层字段
paragraphs 是否为空
event_graph.events 是否为空
事件 / 候选 / voice_line / video_unit / evidence 的 ID 引用是否存在
```

---

# 02 真实执行机制

## 真实 LLM

02 不支持正式流程使用占位剧本。必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选：

```bash
set AI_DRAMA_LLM_TEMPERATURE=0.25
```

## 分阶段

```text
02A 改编蓝图
02B 剧本结构
02C 正式剧本
02D 剧本生产标注
02E 总检评分
```

## JSON 修复

LLM 返回 JSON 解析失败时：

```text
02_script_writer/core/json_repair.py 把 broken_json 和错误原因发回 LLM
要求只修复 JSON 格式
```

## 评分与重跑

```text
每阶段生成后 quality_checker.py 评分。
低于阈值时生成 revision_instructions，并把修改意见传回同阶段重跑。
02E 总检如果输出 needs_retry=true 和 retry_stages，会从最早有问题的阶段开始，连同后续阶段再跑一轮。
```

示例：

```text
02E 发现剧本结构压缩过狠 → retry_stages = ["02B"]
系统会重跑：02B → 02C → 02D → 02E
```

## 硬规则校验

最终合并后 `schema_validator.py` 检查：

```text
必要顶层字段
segments 是否为空
segment_id 是否缺失或重复
segment type 是否合法
对白 segment 是否有 speaker
script_text 是否为空
audio_cues / storyboard_hints 是否引用真实 segment_id
event_coverage_map 是否为空
```

---

# 下一步计划

进入统一测试阶段。

建议本地测试前先配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

先测试 01：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
```

再测试 02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
```

或完整测试 01→02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

---

# 用户最新明确要求

```text
先把所有子系统的框架都弄起来，再一次性测试，慢慢精细打磨每一步。
每一步改动都写入 README 或文档。
后续尽量连续修改，不需要每一次小改动都让用户点击确认。
01 必须通读用户给出的内容，理解到底说的是什么。
角色/场景/道具候选越详细越好，不怕多，怕遗漏。
只要文章里面提到的人、地点、物件都需要提取出来作为候选。
为了最终视频讲的故事质量，story_spine、viewer_experience_plan、information_reveal_plan、character_arc_map、scene_value_map、golden_lines、confusion_risk_report、adaptation_strategy 这 8 个字段都需要。
01 不能一次塞所有内容给 LLM；必须分阶段使用不同输入和不同提示词。
所有需要 LLM 的 01A–01F 都必须真实调用 LLM，不允许占位文件。
评分必须给出修改意见，并能让 LLM 按修改意见再执行。
先完成 01 的理论搭建，后续再根据具体数据精修。
02 是剧本改编系统，重点生成正式剧本，不是分镜系统、资产系统或视频系统。
02 必须延续 01 的分阶段真实 LLM + 评分 + 修改意见重跑机制。
02 必须防止剧本压缩过狠，不能把多个关键事件压成一句话。
```
