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

# 最高前置任务：通读全文，理解故事

01 不能只是机械切段、提取人物、提取场景。

它必须先完成一件事：

```text
通读用户给出的全部内容，理解故事整体到底在讲什么。
```

否则后续 02 剧本系统容易只抓局部爆点，把故事改偏。

因此 `novel_analysis.json` 顶层必须包含：

```text
story_understanding
```

它用于回答：

```text
这篇故事一句话讲什么
全文主线是什么
主角是谁
主角开局处境是什么
主角真正经历了什么变化
核心矛盾是什么
底层主题是什么
世界规则是什么
主要人物关系真实作用是什么
哪些地方绝对不能误读
后续改编必须遵守哪些护栏
```

---

# 最高故事质量任务：让视频讲的故事好看、清楚、留人

01 不直接写剧本，但必须为 02 提供故事质量控制字段。

schema 1.2 必须包含 8 个故事质量字段：

```text
story_spine
viewer_experience_plan
information_reveal_plan
character_arc_map
scene_value_map
golden_lines
confusion_risk_report
adaptation_strategy
```

用途：

```text
story_spine：保证故事不散，有清晰主轴
viewer_experience_plan：保证观众情绪路线清楚
information_reveal_plan：保证悬念、秘密、反转不会太早或太晚揭露
character_arc_map：保证视频讲的是人物变化，不只是事件堆叠
scene_value_map：判断每场戏的作用，防止平均用力
golden_lines：提取原文狠话、金句、关键信息句，防止原文味道丢失
confusion_risk_report：提前标记观众可能看不懂的地方
adaptation_strategy：给 02 一个总体改编策略，但不直接写剧本
```

---

# 最高候选提取规则：提到就提取

角色、场景、道具候选采用全量提取策略。

最高规则：

```text
只要文章里提到过的人、地点、物件，都必须提取出来作为候选。
```

01 不负责筛掉“不重要”的候选。

```text
重要性只作为 importance 字段评分
不能作为是否提取的门槛
```

也就是说：

```text
只出现一次的人，也要提取
没有名字但有称谓的人，也要提取
群体角色，也要提取
只提到但没正式出场的地点，也要提取
只出现一句的场景，也要提取
只被提到但没使用的物件，也要提取
衣服、令牌、信件、钱袋、家具、灯具、门窗等，只要文章提到，也要提取
```

后续处理分工：

```text
01：全量提取候选，宁可多，不可漏
03：角色候选合并、去重、标准化
04：场景候选合并、去重、标准化
05：道具候选合并、去重、标准化
```

候选过多不是错误。

```text
文章提到过的人、地点、物件没有进入候选，才是 01 需要返工的问题。
```

---

# 重要：01 不允许一次大 prompt 完成

01 的最终输出很多，但不能一次把所有内容都塞给 LLM。

错误做法：

```text
一个超大 prompt + 全文小说 → 一次生成完整 novel_analysis.json
```

这样容易导致：

```text
漏字段
漏角色/场景/道具候选
JSON 截断
前后理解不一致
把解析和改写混在一起
只抓局部爆点，忽略全文主线
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

# 01 分阶段 LLM 工作流

## 01A：全文理解阶段

输入：

```text
完整 novel.txt
```

提示词目标：

```text
只理解全文，不提取全量候选，不写剧本。
```

输出：

```text
story_understanding
story_spine
viewer_experience_plan
information_reveal_plan
adaptation_strategy
misread_prevention
```

作用：

```text
先确定故事到底讲什么，主角是谁，核心矛盾是什么，故事主轴是什么，信息释放怎么控制。
```

---

## 01B：段落切分阶段

输入：

```text
完整 novel.txt
```

提示词目标：

```text
只切段，不总结，不改写。
```

输出：

```text
chapters
paragraphs
timeline 初步标记
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

作用：

```text
后续所有事件、候选、金句、证据都必须能回到 paragraph_id。
```

---

## 01C：事件图谱阶段

输入：

```text
story_understanding
story_spine
paragraphs
```

提示词目标：

```text
只提取事件、因果、冲突、高留存片段，不提取全量资产候选。
```

输出：

```text
event_graph
conflicts
high_retention_segments
scene_value_map
character_arc_map
```

作用：

```text
搞清楚故事怎么推进，哪些事件是因果、反转、铺垫、回忆、插叙，哪些戏值得后续重点改编。
```

---

## 01D：全量候选提取阶段

输入：

```text
paragraphs
event_graph
candidate_extraction_policy
```

提示词目标：

```text
只提取文章里提到过的全部人、地点、物件。
不筛选，不压缩，不最终合并。
```

输出：

```text
candidate_characters
candidate_scenes
candidate_props
asset_binding_hints
visual_risk_report
```

建议执行方式：

```text
按段落批量提取
或按事件批量提取
最后程序汇总候选
```

硬规则：

```text
只要文章里提到过，就必须输出为候选。
不确定也要输出，confidence 可以低。
```

---

## 01E：声音和视频生产预判阶段

输入：

```text
story_understanding
story_spine
event_graph
paragraphs
golden_lines 初稿
```

提示词目标：

```text
不写正式剧本，只判断哪些原文信息适合变成旁白、对白、心理 OS、留白，以及哪些事件适合 6–12 秒视频单元。
```

输出：

```text
voice_line_candidates
video_unit_candidates
emotion_curve
golden_lines
confusion_risk_report
```

作用：

```text
提前服务 02 剧本、08 音频、09 视频，避免后面才发现台词太长、事件太挤、观众看不懂。
```

---

## 01F：汇总校验阶段

输入：

```text
01A–01E 的所有中间结果
paragraphs
原文 novel.txt
```

提示词目标：

```text
检查遗漏、矛盾、误读、JSON 缺字段、证据不足。
```

输出：

```text
evidence_index
quality_report
warnings
chapter_memory_update
最终 novel_analysis.json
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

# 01 内部建议目录结构

后续精修 01 时，可以按下面结构拆：

```text
01_novel_parser/
  run.py
  prompts/
    01A_story_understanding.md
    01B_paragraph_split.md
    01C_event_graph.md
    01D_candidate_extract.md
    01E_production_predict.md
    01F_quality_check.md
  core/
    llm_client.py
    paragraph_splitter.py
    schema_builder.py
    stage_runner.py
    candidate_merger.py
    evidence_builder.py
    quality_checker.py
  intermediate/
    01A_story_understanding.json
    01B_paragraphs.json
    01C_event_graph.json
    01D_candidates.json
    01E_production_predict.json
    01F_quality_check.json
```

注意：这只是 01 内部步骤，不是新建 01A–01F 子系统。

---

# novel_analysis.json 当前结构

当前 schema：

```text
schema_version = 1.2
```

顶层结构：

```json
{
  "schema_version": "1.2",
  "module": "01_novel_parser",
  "status": "success",
  "source_status": "input_found",
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
  "event_graph": {
    "events": [],
    "event_edges": [],
    "main_event_path": [],
    "side_event_paths": []
  },
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

```text
01_novel_parser/novel_analysis.json
        ↓
02_script_writer/script.json
        ↓
03_character_library/characters.json
        ↓
04_scene_library/scenes.json
        ↓
05_prop_library/props.json
        ↓
06_storyboard/storyboard.json
```

后续模块必须优先参考：

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
candidate_extraction_policy
event_graph
evidence_index
```

尤其是 02 剧本改编系统，不得为了刺激感违背 01 对全文主线、主角旅程、故事主轴、信息释放和人物弧光的理解。

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

# 是否使用本地模型

未来会使用本地 LLM。

当前框架版本只输出 scaffold 结构。

---

# 显存释放

本模块未来会调用本地 LLM。

运行结束后必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

当前 `run.py` 已经内置该释放逻辑。
