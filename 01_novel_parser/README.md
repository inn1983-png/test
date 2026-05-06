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

# novel_analysis.json 建议结构

```json
{
  "schema_version": "1.0",
  "module": "01_novel_parser",
  "status": "success",
  "source_status": "input_found",
  "input_convention": "input/novel.txt",
  "novel": {},
  "story_understanding": {},
  "chapters": [],
  "paragraphs": [],
  "events": [],
  "conflicts": [],
  "high_retention_segments": [],
  "candidate_characters": [],
  "candidate_scenes": [],
  "candidate_props": [],
  "timeline": [],
  "emotion_curve": [],
  "adaptation_hints": {},
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

# 主要任务

1. 通读全文，理解故事整体
2. 识别章节信息
3. 切分段落并保留原文索引
4. 提取事件链
5. 提取关键冲突
6. 标记高留存 / 高刺激片段
7. 提取人物候选清单
8. 提取场景候选清单
9. 提取道具候选清单
10. 提取时间线
11. 提取情绪节奏
12. 给 02 剧本系统提供改编建议，但不直接改写

---

# 最高原则

本模块只做“理解 + 解析”，不做“改编”。

禁止在本模块里：

- 改写小说
- 扩写剧情
- 压缩成剧本
- 生成分镜
- 生成图像提示词
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
