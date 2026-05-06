# 01 小说解析系统

## 模块定位

01 小说解析系统是整个流水线的第一步。

它不负责写剧本，不负责分镜，不负责生成角色图，不负责生成视频提示词。

它只负责：

```text
先通读用户给出的小说内容
理解这篇到底讲的是什么
再把原始小说文本拆干净
提取后续模块需要的基础信息
为最终视频故事质量提供控制信息
```

---

# 当前理论完成状态

01 当前已完成理论架构闭合：

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

后续需要根据真实小说数据和本地模型表现继续精修 prompt、阈值、分批大小和评分规则。

---

# 当前实际运行入口

当前 00 总控会优先运行模块内的：

```text
run_staged.py
```

如果模块没有 `run_staged.py`，才回退运行：

```text
run.py
```

因此 01 当前正式 pipeline 入口是：

```text
01_novel_parser/run_staged.py
```

---

# 01 必须真实调用 LLM

01 不再支持 scaffold 占位解析。

凡是 01A–01F 需要理解、切分标注、事件分析、候选提取、预判、评分的步骤，都必须真实调用 LLM。

如果没有配置本地 LLM，01 应该直接失败，不允许继续生成占位 `novel_analysis.json`。

必须配置环境变量：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选配置：

```bash
set AI_DRAMA_LLM_API_KEY=你的 key，没有可不填
set AI_DRAMA_LLM_TIMEOUT_SEC=180
set AI_DRAMA_LLM_TEMPERATURE=0.2
```

输入文件必须存在且非空：

```text
input/novel.txt
```

---

# 已落地的工程结构

```text
01_novel_parser/
  run_staged.py
  core/
    __init__.py
    llm_client.py
    json_repair.py
    paragraph_splitter.py
    chunk_manager.py
    quality_checker.py
    schema_validator.py
    stage_runner.py
  prompts/
    01A_story_understanding.md
    01B_paragraph_split.md
    01C_event_graph.md
    01D_candidate_extract.md
    01E_production_predict.md
    01F_quality_check.md
  input/
    novel.txt.example
  tests/
    README.md
```

运行后会生成：

```text
intermediate/01A_story_understanding.json
intermediate/01B_paragraphs.json
intermediate/01C_event_graph.json
intermediate/01D_batch_XXX_candidates.json
intermediate/01D_candidates.json
intermediate/01E_production_predict.json
intermediate/01F_quality_check.json
```

最终合并为：

```text
novel_analysis.json
```

---

# 01B：程序切段 + LLM 标注

01B 不再完全依赖 LLM 决定段落边界。

当前流程：

```text
paragraph_splitter.py 先按原文生成稳定 paragraph_id / text / start_char / end_char
LLM 只负责补充 chapters / paragraph_type / timeline / 标注属性
merge_llm_paragraph_annotations 保留程序段落边界
```

这样可以保证后续所有事件、候选、金句、证据都能稳定回链到 `paragraph_id`。

---

# 01D：分批全量候选提取

01D 不再一次把所有 paragraphs 塞给 LLM。

当前流程：

```text
chunk_manager.py 按段落分批
每个 batch 调用 01D_candidate_extract.md
每批输出候选角色 / 场景 / 道具
程序合并所有 batch 候选
不删除不确定重复项，只标记 source_batch_id / possible_same_as
```

最高规则仍然是：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
不确定也要输出，confidence 可以低。
importance 只表示后续优先级，不能作为是否提取的门槛。
```

候选过多不是错误，遗漏才是错误。

---

# JSON 修复机制

`llm_client.py` 会尝试解析 LLM 返回 JSON。

如果解析失败：

```text
json_repair.py 会把 broken_json 和错误原因发回 LLM
要求只修复 JSON 格式
再重新解析
```

该机制只修复格式，不新增业务内容。

---

# 评分与重跑机制

01 有两层修正机制。

## 第一层：阶段内评分重跑

每个阶段生成后，`quality_checker.py` 会检查：

```text
必要字段是否存在
JSON 是否符合阶段结构
候选是否为空
paragraphs 是否为空
story_understanding 是否完整
```

如果分数低于阈值，会生成：

```text
revision_instructions
```

然后把修改意见传回同一阶段，让 LLM 重新执行。

## 第二层：01F 总检触发阶段重跑

01F 会检查 01A–01E 的总结果。

如果 01F 输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["01D"],
    "revision_instructions": []
  }
}
```

`stage_runner.py` 会从最早需要重跑的阶段开始，连同后续阶段再执行一轮。

例如：

```text
01F 发现候选漏提 → retry_stages = ["01D"]
系统会重跑：01D → 01E → 01F
```

---

# 最终硬规则校验

最终合并 `novel_analysis.json` 后，`schema_validator.py` 会做程序级硬校验：

```text
顶层必要字段是否存在
paragraphs 是否为空
event_graph.events 是否为空
event.paragraph_ids 是否引用真实 paragraph_id
event_edges 是否引用真实 event_id
候选 raw_mentions / appearance_paragraphs 是否引用真实 paragraph_id
voice_line 是否引用真实 paragraph_id / event_id
video_unit 是否引用真实 event_id
evidence_index 是否引用真实 paragraph_id
```

校验结果写入：

```text
schema_validation
quality_report.schema_validation_passed
quality_report.schema_validation_issues
```

---

# 最高原则

01 只做：

```text
理解 + 解析 + 故事质量控制 + 生产预判
```

01 禁止做：

```text
改写小说
扩写剧情
压缩成剧本
生成正式剧本
生成分镜
生成图像提示词
生成视频提示词
直接写入 shared_assets
```

---

# 重要：01 不允许一次大 prompt 完成

01 的最终输出很多，但不能一次把所有内容都塞给 LLM。

错误做法：

```text
一个超大 prompt + 全文小说 → 一次生成完整 novel_analysis.json
```

正确做法：

```text
多阶段解析
每一阶段给 LLM 不同输入
每一阶段使用不同提示词
每一阶段输出不同中间结果
最后由程序合并成 novel_analysis.json
```

---

# 01A–01F 分阶段工作流

## 01A：全文理解阶段

输入：完整 `novel.txt`

输出：

```text
story_understanding
story_spine
viewer_experience_plan
information_reveal_plan
adaptation_strategy
misread_prevention
```

## 01B：段落切分标注阶段

输入：

```text
完整 novel.txt
程序生成的 base_split
```

输出：

```text
chapters
paragraphs
timeline
```

程序锁定：

```text
paragraph_id
text
start_char
end_char
```

LLM 标注：

```text
chapter 信息
paragraph_type
contains_dialogue
contains_action
contains_new_character
contains_new_scene
contains_new_prop
timeline
```

## 01C：事件图谱阶段

输入：

```text
story_understanding
story_spine
paragraphs
```

输出：

```text
event_graph
conflicts
high_retention_segments
scene_value_map
character_arc_map
```

## 01D：全量候选提取阶段

输入：

```text
paragraph batch
event_graph
candidate_extraction_policy
```

输出：

```text
candidate_characters
candidate_scenes
candidate_props
asset_binding_hints
visual_risk_report
```

## 01E：声音和视频生产预判阶段

输入：

```text
story_understanding
story_spine
event_graph
paragraphs
golden_lines 初稿
```

输出：

```text
voice_line_candidates
video_unit_candidates
emotion_curve
golden_lines
confusion_risk_report
```

## 01F：汇总校验阶段

输入：

```text
01A–01E 的所有中间结果
paragraphs
原文 novel.txt
```

输出：

```text
evidence_index
quality_report
warnings
chapter_memory_update
```

---

# schema 1.2 顶层结构

```json
{
  "schema_version": "1.2",
  "module": "01_novel_parser",
  "status": "success / needs_review",
  "source_status": "input_found",
  "stage_mode": "llm",
  "stage_status": [],
  "final_revision_rounds": [],
  "schema_validation": {},
  "input": {},
  "novel": {},
  "story_understanding": {},
  "story_spine": {},
  "viewer_experience_plan": {},
  "information_reveal_plan": [],
  "character_arc_map": [],
  "scene_value_map": [],
  "golden_lines": [],
  "confusion_risk_report": {},
  "adaptation_strategy": {},
  "misread_prevention": {},
  "candidate_extraction_policy": {},
  "chapters": [],
  "paragraphs": [],
  "event_graph": {},
  "events": [],
  "conflicts": [],
  "high_retention_segments": [],
  "candidate_characters": [],
  "candidate_scenes": [],
  "candidate_props": [],
  "voice_line_candidates": [],
  "video_unit_candidates": [],
  "asset_binding_hints": [],
  "timeline": [],
  "emotion_curve": [],
  "visual_risk_report": {},
  "evidence_index": [],
  "adaptation_hints": {},
  "chapter_memory_update": {},
  "quality_report": {},
  "warnings": []
}
```

---

# 与后续模块的关系

核心依赖：

```text
02：story_understanding / story_spine / adaptation_strategy / golden_lines
03：candidate_characters
04：candidate_scenes
05：candidate_props
06：event_graph / scene_value_map / asset_binding_hints
08：voice_line_candidates / emotion_curve / golden_lines
09：video_unit_candidates / visual_risk_report
10：story_spine / viewer_experience_plan / information_reveal_plan / confusion_risk_report
```

---

# 输入

正式 pipeline 输入：

```text
workspace/projects/{project_id}/input/novel.txt
```

长篇章节模式：

```text
workspace/books/{book_id}/chapters/{chapter_id}/input/novel.txt
```

单模块调试输入：

```text
01_novel_parser/input/novel.txt
```

---

# 输出

正式 pipeline 输出：

```text
workspace/projects/{project_id}/01_novel_parser/novel_analysis.json
```

长篇章节模式：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/novel_analysis.json
```

单模块调试输出：

```text
01_novel_parser/output/novel_analysis.json
```

---

# 测试

测试样例：

```text
01_novel_parser/input/novel.txt.example
```

测试清单：

```text
01_novel_parser/tests/README.md
```

建议单模块测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
```

---

# 显存释放

本模块会调用本地 LLM。

运行结束后必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

当前 `run_staged.py` 已经内置该释放逻辑。
