# 01 小说解析系统

## 模块定位

小说解析系统是整个流水线的第一步。

它不负责写剧本，不负责分镜，不负责生成角色图。

它只负责：

```text
先通读用户给出的小说内容
理解这篇到底讲的是什么
再把原始小说文本拆干净
提取后续模块需要的基础信息
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

`story_understanding` 用于回答：

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

# 输入

正式 pipeline 输入：

```text
workspace/projects/{project_id}/input/novel.txt
```

或长篇章节模式：

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

或长篇章节模式：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/novel_analysis.json
```

单模块调试输出：

```text
01_novel_parser/output/novel_analysis.json
```

---

# novel_analysis.json 当前结构

当前 schema：

```text
schema_version = 1.1
```

建议顶层结构：

```json
{
  "schema_version": "1.1",
  "module": "01_novel_parser",
  "status": "success",
  "source_status": "input_found",
  "input": {},
  "novel": {},
  "story_understanding": {},
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

# story_understanding 字段

`story_understanding` 是 01 的最高优先级输出。

建议字段：

```json
{
  "requires_full_reading": true,
  "one_sentence_summary": "一句话说明整篇内容到底讲的是什么",
  "full_story_summary": "不改写、不扩写，只概括全文真实主线",
  "core_premise": "故事成立的核心前提",
  "protagonist_journey": {
    "protagonist": "主角是谁",
    "goal": "主角想要什么",
    "misbelief": "主角开局的误解、执念或盲区",
    "start_state": "主角开局处境、身份、误解或欲望",
    "pressure": "主角遭遇的主要压迫或困境",
    "turning_point": "主角认知或命运发生变化的关键点",
    "end_state": "本章或本文末尾主角处境变化"
  },
  "central_conflict": "全文最核心的矛盾，不是局部争吵",
  "deep_theme": "故事真正想表达的底层主题",
  "world_rules": [],
  "relationship_core": [],
  "must_not_misread": [],
  "adaptation_guardrails": []
}
```

---

# candidate_extraction_policy 字段

`candidate_extraction_policy` 用来约束候选提取。

核心策略：

```text
extract_every_mentioned_candidate
```

必须明确：

```text
只要文章提到，就进入候选
不因重要性低而过滤
不因只出现一次而过滤
不因没有名字而过滤
不因只是群体角色而过滤
不因只是被提到但没出场而过滤
```

候选字段至少包含：

```text
candidate_id
name
aliases
candidate_type
mention_type
first_appearance_paragraph
appearance_paragraphs
importance
confidence
raw_mentions
possible_same_as
risk_notes
```

其中：

```text
importance = 后续优先级
confidence = 识别置信度
raw_mentions = 原文提到证据
possible_same_as = 可能和其他候选是同一个，留给后续模块合并
```

---

# event_graph 字段

01 不只输出事件列表，还要输出事件图谱。

```json
{
  "event_graph": {
    "events": [],
    "event_edges": [],
    "main_event_path": [],
    "side_event_paths": []
  }
}
```

事件之间必须记录：

```text
因果
推进
反转
铺垫
回忆
插叙
并行支线
```

---

# voice_line_candidates 字段

01 不写剧本，但要提前判断哪些原文信息适合转成：

```text
N：旁白
D：对白
M：心理 OS
S：留白
```

用于后续 02、08、09 提前考虑音频长度和视频单元切分。

---

# video_unit_candidates 字段

01 不生成视频 JSON，但要预判哪些事件适合成为 6–12 秒视频单元。

每个候选单元应记录：

```text
event_id
voice_line_candidate_ids
main_scene
main_characters
main_action_chain
estimated_duration_sec
target_duration_range_sec
single_scene_required
action_chain_count
needs_split
split_warning
```

---

# visual_risk_report 字段

用于提前标记后续图像/视频容易出错的地方：

```text
性别不明确
年龄不明确
身份不明确
现代物品风险
场景连续性风险
人物数量过多
人物数量不清
道具混淆风险
风格风险
```

---

# evidence_index 字段

01 的关键判断必须尽量回到原文证据。

尤其是：

```text
story_understanding
event_graph
candidate_characters
candidate_scenes
candidate_props
conflicts
high_retention_segments
```

每条证据建议包含：

```text
evidence_id
paragraph_id
raw_text
supports
note
```

---

# 主要任务

1. 通读全文，理解故事整体
2. 识别章节信息
3. 切分段落并保留原文索引
4. 提取事件图谱
5. 提取关键冲突
6. 标记高留存 / 高刺激片段
7. 全量提取人物候选清单
8. 全量提取场景候选清单
9. 全量提取道具候选清单
10. 提取时间线
11. 提取情绪节奏
12. 预判 voice_line_candidates
13. 预判 video_unit_candidates
14. 生成 asset_binding_hints
15. 生成 visual_risk_report
16. 生成 evidence_index
17. 给 02 剧本系统提供改编建议，但不直接改写

---

# 最高原则

本模块只做“理解 + 解析 + 生产预判”，不做“改编”。

禁止在本模块里：

- 改写小说
- 扩写剧情
- 压缩成剧本
- 生成正式剧本
- 生成分镜
- 生成图像提示词
- 生成视频提示词
- 直接写入 shared_assets

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
candidate_extraction_policy
event_graph
evidence_index
```

尤其是 02 剧本改编系统，不得为了刺激感违背 01 对全文主线、主角旅程、核心矛盾的理解。

---

# 清理规则

本模块正式运行数据写入 workspace 下的运行目录。

模块自身：

```text
01_novel_parser/input/
01_novel_parser/output/
```

只用于单模块调试。

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
