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
01 已进入 01A–01F 真实 LLM 分阶段解析框架。
```

01 当前方向：

```text
不是一个大 prompt 生成一个大 JSON。
而是不同阶段给 LLM 不同输入、不同提示词、不同输出，最后由程序合并为 novel_analysis.json。
01 不再支持 scaffold 占位解析。所有 01A–01F 阶段必须真实调用 LLM。
```

---

# 关键架构

## 00 总控

模块运行入口规则：

```text
如果模块目录存在 run_staged.py，00 优先运行 run_staged.py。
否则运行 run.py。
```

该规则用于让复杂模块使用内部分阶段流程，同时不影响其他简单模块。

## 01 小说解析系统

01 当前正式 pipeline 入口：

```text
01_novel_parser/run_staged.py
```

01 真实 LLM 调用层：

```text
01_novel_parser/core/llm_client.py
```

必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

01 阶段执行器：

```text
01_novel_parser/core/stage_runner.py
```

01 阶段评分器：

```text
01_novel_parser/core/quality_checker.py
```

01 分阶段提示词：

```text
01_novel_parser/prompts/01A_story_understanding.md
01_novel_parser/prompts/01B_paragraph_split.md
01_novel_parser/prompts/01C_event_graph.md
01_novel_parser/prompts/01D_candidate_extract.md
01_novel_parser/prompts/01E_production_predict.md
01_novel_parser/prompts/01F_quality_check.md
```

运行后会生成：

```text
intermediate/01A_story_understanding.json
intermediate/01B_paragraphs.json
intermediate/01C_event_graph.json
intermediate/01D_candidates.json
intermediate/01E_production_predict.json
intermediate/01F_quality_check.json
01_novel_parser/novel_analysis.json
```

---

# 01 schema 与核心原则

当前 schema：

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

# 评分与重跑机制

01 有两层修正机制：

```text
1. 每个阶段生成后，quality_checker.py 评分。
2. 如果阶段低于阈值，生成 revision_instructions，并把修改意见传回同一阶段重跑。
3. 01F 做总检，如果输出 needs_retry=true 和 retry_stages，会从最早有问题的阶段开始，连同后续阶段再跑一轮。
```

示例：

```text
01F 发现候选漏提 → retry_stages=["01D"]
系统重跑 01D → 01E → 01F
```

---

# 已完成关键改动

## 2026-05-07：初始化 00–10 模块框架

- 创建 00–10 模块目录
- 创建 00_common 公共工具层
- 创建 pipeline.json
- 创建 01–10 基础 run.py
- 加入资源释放逻辑

## 2026-05-07：完成 00 总控基座

- 支持短篇项目和长篇章节两种模式
- 支持 shared_assets / global_memory
- 支持 manifest + SQLite artifacts.db
- 支持 run_status.json
- 支持 pipeline 校验、依赖检查、dry-run、局部运行
- 支持清理、查询、自检、资源释放配置

## 2026-05-07：打通 01–10 scaffold 闭环

- 01 输出 novel_analysis.json
- 02 输出 script.json
- 03 输出 characters.json
- 04 输出 scenes.json
- 05 输出 props.json
- 06 输出 storyboard.json
- 07 输出 image_manifest.json
- 08 输出 final_audio.wav
- 09 输出 video_manifest.json
- 10 输出 final.mp4
- 所有关键产物登记到 manifest.key_outputs 和 artifacts.db

## 2026-05-07：01 升级到 schema 1.2

- 增加全局故事理解 story_understanding
- 增加故事质量控制字段
- 增加事件图谱 event_graph
- 增加全量候选提取策略
- 增加声音/视频生产预判
- 增加证据链和质量报告

## 2026-05-07：01 改为真实 LLM 分阶段解析框架

- 新增 `01_novel_parser/run_staged.py`
- 新增 `01_novel_parser/core/llm_client.py`
- 新增 `01_novel_parser/core/stage_runner.py`
- 新增 `01_novel_parser/core/quality_checker.py`
- 新增 01A–01F 六个真实 JSON 输出 prompt
- 移除 01 scaffold 占位回退逻辑
- 01 缺少 LLM 配置或 input/novel.txt 为空时直接失败
- 每阶段评分，低分按修改意见重跑
- 01F 总检可触发目标阶段及后续阶段再执行一轮
- 更新 `00_common/module_runner.py`，优先运行 run_staged.py
- 更新 `01_novel_parser/README.md`

---

# 下一步计划

建议本地测试前先配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

然后准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

再运行：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
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
```
