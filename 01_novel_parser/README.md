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

凡是 01A–01F 需要理解、切分、提取、预判、评分的步骤，都必须真实调用 LLM。

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

# 已落地的阶段结构

```text
01_novel_parser/
  run_staged.py
  core/
    __init__.py
    llm_client.py
    quality_checker.py
    stage_runner.py
  prompts/
    01A_story_understanding.md
    01B_paragraph_split.md
    01C_event_graph.md
    01D_candidate_extract.md
    01E_production_predict.md
    01F_quality_check.md
```

运行后会额外生成：

```text
intermediate/01A_story_understanding.json
intermediate/01B_paragraphs.json
intermediate/01C_event_graph.json
intermediate/01D_candidates.json
intermediate/01E_production_predict.json
intermediate/01F_quality_check.json
```

最终合并为：

```text
novel_analysis.json
```

---

# 评分与重跑机制

01 有两层修正机制。

## 第一层：阶段内评分重跑

每个阶段生成后，`quality_checker.py` 会检查：

```text
必要字段是否存在
JSON 是否符合阶段结构
是否仍是占位内容
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

这样不是只给分，而是会根据修改意见自动修正。

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

## 01B：段落切分阶段

输入：完整 `novel.txt`

输出：

```text
chapters
paragraphs
timeline
```

每个段落必须有：

```text
paragraph_id
chapter_id
index
text
start_char
end_char
paragraph_type
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
paragraphs
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

最高规则：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
不确定也要输出，confidence 可以低。
importance 只表示后续优先级，不能作为是否提取的门槛。
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

重点检查：

```text
故事主轴是否清楚
主角是否明确
事件图谱是否断裂
时间线是否混乱
文章提到的人、地点、物件是否全部进入候选
金句是否漏掉
所有关键判断是否能回查 paragraph_id
是否需要重跑某一阶段
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

# 显存释放

本模块会调用本地 LLM。

运行结束后必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

当前 `run_staged.py` 已经内置该释放逻辑。
