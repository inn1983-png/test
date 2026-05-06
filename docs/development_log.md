# 开发记录与协作规则

本文档记录每一轮框架改动，方便用户、新对话、本地 Codex 接手。

---

# 协作规则

1. 每一轮改动前，先简要说明准备做什么。
2. 用户可以随时补充要求。
3. 每一轮重要改动后，必须写入 README 或 docs 文档。
4. 不只改代码，也要同步更新说明。
5. 每个模块必须说明：模块定位、输入、输出、与其他模块关系、清理规则、是否使用本地模型、是否需要释放显存。
6. 00 总控层的改动必须优先写清楚，因为它决定所有后续模块的运行方式。
7. 后续采用连续开发模式：在用户给出明确方向后，可以连续修改代码和文档，不需要每一个小改动都反复询问确认。
8. 需要提前确认的情况仅限：删除大量文件、重构核心架构、改变模块边界、修改已确定的数据目录规则、可能破坏现有可运行流程的改动。
9. 每一轮完成后，必须总结本轮具体做了什么、修改了哪些文件、下一步建议做什么。

---

# 当前开发阶段

当前阶段：00 + 01–10 子系统框架已能闭环；01 已升级到 schema 1.2。

01 当前方向：

```text
全文理解
故事质量控制
事件图谱
全量候选提取
音频/视频生产预判
原文证据链
```

01 schema 1.2 已包含：

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
misread_prevention
candidate_extraction_policy
event_graph
voice_line_candidates
video_unit_candidates
asset_binding_hints
visual_risk_report
evidence_index
chapter_memory_update
quality_report
```

建议用户在本地执行：

```bash
python 00_main_controller/self_check.py
```

如果通过，再执行真实项目测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001
```

---

# 已完成改动

## 2026-05-07：初始化模块化总框架

- 创建 00–10 模块目录
- 创建总 README、pipeline.json、requirements.txt、.gitignore、.env.example
- 创建 00_common 公共工具层
- 为每个模块创建基础 run.py
- 为每个模块加入资源释放逻辑

## 2026-05-07：补充模块说明文档

- 新增 docs/codex_handoff.md
- 新增 docs/module_isolation.md
- 新增 docs/project_workspace.md
- 新增 01–10 各模块 README

核心规则：

```text
一个文件夹 = 一个独立子系统
模块代码和运行数据分离
长篇小说使用 shared_assets 共享资产库
每个本地模型模块跑完必须释放显存
```

## 2026-05-07：打磨 00 总控基座

- 支持短篇项目模式：workspace/projects/{project_id}/
- 支持长篇章节模式：workspace/books/{book_id}/chapters/{chapter_id}/
- 长篇模式自动创建 shared_assets / global_memory
- 初始化 runtime_context.json / manifest.json / artifacts.db / run_status.json
- 支持 pipeline 校验、模块调度、依赖检查、局部运行、dry-run
- 支持安全清理、产物查询、空流程自检、完整框架闭环自检
- 支持本地资源释放配置

## 2026-05-07：01–10 子系统框架闭环

- 01 输出 novel_analysis.json
- 02 输出 script.json
- 03 输出 characters.json
- 04 输出 scenes.json
- 05 输出 props.json
- 06 输出 storyboard.json
- 07 输出 image_manifest.json，并生成占位 shot_001.png
- 08 输出 final_audio.wav，并生成 audio_manifest.json
- 09 输出 video_manifest.json，并生成占位 clip_001.mp4
- 10 输出 final.mp4，并生成 assembly_manifest.json
- 所有关键产物登记到 manifest.key_outputs 和 artifacts.db

## 2026-05-07：记录连续开发协作偏好

- 用户给出明确方向后，可以连续修改代码和文档
- 不需要每一个小改动都反复询问确认
- 删除大量文件、重构核心架构、改变模块边界、修改数据目录规则、可能破坏现有可运行流程时，需要先确认
- 每轮完成后必须总结做了什么、改了哪些文件、下一步建议

## 2026-05-07：01 增加全局故事理解 story_understanding

- 01 的最高前置任务改为：先通读用户给出的全部内容，理解故事整体到底在讲什么
- novel_analysis.json 顶层新增 story_understanding
- story_understanding 记录全文主线、主角旅程、核心矛盾、底层主题、世界规则、关系核心、误读风险、改编护栏
- 后续 02 剧本改编必须优先服从 story_understanding

## 2026-05-07：01 升级 schema 1.1 与全量候选提取规则

- novel_analysis.json schema_version 升级为 1.1
- 新增 misread_prevention、candidate_extraction_policy、event_graph、voice_line_candidates、video_unit_candidates、asset_binding_hints、visual_risk_report、evidence_index、chapter_memory_update
- candidate_characters / candidate_scenes / candidate_props 增加更详细的候选字段

候选提取最高规则：

```text
只要文章里提到过的人、地点、物件，都必须提取出来作为候选。
重要性只作为 importance 字段评分，不能作为是否提取的门槛。
候选过多不算错误；文章提到过的人、地点、物件没有进入候选，才需要返工。
01 不负责最终筛选、合并、去重。03/04/05 负责候选合并、去重、标准化。
```

## 2026-05-07：01 升级 schema 1.2 与故事质量控制字段

- novel_analysis.json schema_version 升级为 1.2
- 新增 story_spine，用于固定故事主轴
- 新增 viewer_experience_plan，用于规划观众情绪体验
- 新增 information_reveal_plan，用于控制秘密、反转、身份、规则的信息释放顺序
- 新增 character_arc_map，用于记录人物弧光和变化
- 新增 scene_value_map，用于判断每场戏的故事价值、视觉价值、对白价值、情绪价值
- 新增 golden_lines，用于提取原文金句、狠话、关键信息句
- 新增 confusion_risk_report，用于提前标记观众可能看不懂的地方
- 新增 adaptation_strategy，用于给 02 剧本系统总体改编策略
- quality_report 增加 story_quality_readiness_score 和上述 8 个字段的存在标记

故事质量目标：

```text
01 不只要把素材提全，还要判断哪些内容让故事好看、清楚、留人。
story_spine 保证故事不散。
information_reveal_plan 保证悬念和反转不被提前说破。
golden_lines 保证原文味道不丢。
confusion_risk_report 保证观众看得懂。
adaptation_strategy 保证 02 有明确改编方向。
```

---

# 下一步计划

下一步建议先本地一次性测试框架闭环。

测试通过后，再继续精修 01 小说解析系统：

1. 设计 01 的本地 LLM 提示词
2. 接入段落切分
3. 接入 story_understanding 真实生成
4. 接入 story_spine / story_quality 字段真实生成
5. 接入 event_graph 真实生成
6. 接入全量角色 / 场景 / 道具候选提取
7. 接入冲突点、高留存片段、voice_line/video_unit 预判
8. 确保所有输出都服从 story_understanding 和 story_spine
9. 确保所有候选都带 raw_mentions / appearance_paragraphs / evidence_index

---

# 用户最新补充要求

```text
先把所有子系统的框架都弄起来，再一次性测试，慢慢精细打磨每一步。
每一步改动都写入 README 或文档。
后续尽量连续修改，不需要每一次小改动都让用户点击确认。
01 必须通读用户给出的内容，理解到底说的是什么。
角色/场景/道具候选提取越详细越好，不怕多，怕遗漏。
只要文章里面提到的都需要提取出来作为候选。
为了最终视频讲的故事质量，story_spine、viewer_experience_plan、information_reveal_plan、character_arc_map、scene_value_map、golden_lines、confusion_risk_report、adaptation_strategy 这 8 个字段都需要。
```
