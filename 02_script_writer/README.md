# 02 剧本改编系统

## 模块定位

02 剧本改编系统负责把 01 小说解析结果改编为适合短视频 / 横屏短剧 / AI 漫剧生产的正式剧本。

它是成片留存的核心模块，但边界必须清楚：

```text
02 负责：剧本改编、对白、OS、留白、动作、情绪、剧本生产标注。
02 不负责：角色资产库、场景资产库、道具资产库、正式分镜、图片生成、视频生成、ComfyUI 调用。
```

02D 中的 `storyboard_hints` 只是剧本层面的画面动作锚点，方便 06 分镜系统继续使用，不是正式分镜，也不是图像提示词。

---

# 当前理论完成状态

02 当前已完成理论架构搭建：

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

后续需要根据真实小说解析结果和本地模型表现继续精修 prompt、评分阈值、剧本长度控制和对白质量规则。

---

# 当前实际运行入口

00 总控会优先运行模块内的：

```text
run_staged.py
```

如果模块没有 `run_staged.py`，才回退运行：

```text
run.py
```

因此 02 当前正式 pipeline 入口是：

```text
02_script_writer/run_staged.py
```

旧的 `run.py` 仍是 scaffold 占位入口，但正式流程应使用 `run_staged.py`。

---

# 02 必须真实调用 LLM

02 不再支持 scaffold 占位剧本作为正式结果。

凡是 02A–02E 需要改编、结构设计、剧本生成、标注、评分的步骤，都必须真实调用 LLM。

如果没有配置本地 LLM，02 应该直接失败，不允许继续生成占位 `script.json`。

必须配置环境变量：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选配置：

```bash
set AI_DRAMA_LLM_API_KEY=你的 key，没有可不填
set AI_DRAMA_LLM_TIMEOUT_SEC=180
set AI_DRAMA_LLM_TEMPERATURE=0.25
```

---

# 已落地的工程结构

```text
02_script_writer/
  run_staged.py
  run.py
  core/
    __init__.py
    llm_client.py
    json_repair.py
    quality_checker.py
    schema_validator.py
    stage_runner.py
  prompts/
    02A_adaptation_blueprint.md
    02B_script_structure.md
    02C_script_draft.md
    02D_production_annotations.md
    02E_quality_check.md
```

运行后会生成：

```text
intermediate/02A_adaptation_blueprint.json
intermediate/02B_script_structure.json
intermediate/02C_script_draft.json
intermediate/02D_production_annotations.json
intermediate/02E_quality_check.json
```

最终合并为：

```text
script.json
script.txt
script_meta.json
```

---

# 输入

02 的核心输入是 01 的：

```text
01_novel_parser/novel_analysis.json
```

正式 pipeline 中，02 会优先读取模块输入目录下的：

```text
02_script_writer/novel_analysis.json
```

如果不存在，会兜底读取当前 run_dir 下的：

```text
01_novel_parser/novel_analysis.json
```

02 重点使用 01 的以下字段：

```text
story_understanding
story_spine
viewer_experience_plan
information_reveal_plan
adaptation_strategy
events
event_graph
conflicts
high_retention_segments
scene_value_map
character_arc_map
golden_lines
voice_line_candidates
video_unit_candidates
emotion_curve
visual_risk_report
paragraphs
```

---

# 输出

正式 pipeline 输出目录：

```text
workspace/projects/{project_id}/02_script_writer/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/
```

关键输出：

```text
script.json       # 结构化剧本关键输出
script.txt        # 可读剧本文本
script_meta.json  # 阶段状态、评分、重跑记录、schema 校验
```

---

# 02A–02E 分阶段工作流

## 02A：改编蓝图阶段

输入：

```text
01 novel_analysis 核心故事信息
```

输出：

```text
adaptation_blueprint
coverage_plan
tone_plan
compression_guardrails
```

目标：先决定怎么改，明确保留哪些关键事件和冲突，防止 3000 字内容被强行压成过短剧本。

## 02B：剧本结构阶段

输入：

```text
01 novel_analysis
02A adaptation_blueprint
```

输出：

```text
script_structure
scene_beats
event_coverage_map
retention_design
```

目标：把故事拆成可写剧本的节拍，并明确每个事件被哪个 beat 覆盖。

## 02C：正式剧本阶段

输入：

```text
01 novel_analysis
02A adaptation_blueprint
02B script_structure
```

输出：

```text
script
segments
script_text
```

正式剧本结构：

```text
【OS】旁白 / 心理独白
【角色名】对白
【留白】节奏停顿
【动作】画面动作
【情绪】语气和表演方向
```

## 02D：剧本生产标注阶段

输入：

```text
02C script_draft
```

输出：

```text
production_annotations
audio_cues
storyboard_hints
risk_report
```

说明：02D 只做剧本标注，不生成正式分镜、不生成图像提示词、不生成视频提示词。

## 02E：总检评分阶段

输入：

```text
01 novel_analysis
02A–02D 所有中间结果
```

输出：

```text
quality_report
evidence_index
warnings
revision_plan
```

如果发现问题，会输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["02B"],
    "revision_instructions": []
  }
}
```

`stage_runner.py` 会从最早需要重跑的阶段开始，连同后续阶段再执行一轮。

例如：

```text
02E 发现剧本结构压缩过狠 → retry_stages = ["02B"]
系统会重跑：02B → 02C → 02D → 02E
```

---

# 评分与重跑机制

02 有两层修正机制。

## 第一层：阶段内评分重跑

每个阶段生成后，`quality_checker.py` 会检查：

```text
必要字段是否存在
结构是否为空
02C 是否包含 OS / dialogue / blank
02D 是否包含 audio_cues / storyboard_hints
02E 是否要求重跑
```

如果分数低于阈值，会生成：

```text
revision_instructions
```

然后把修改意见传回同一阶段，让 LLM 重新执行。

## 第二层：02E 总检触发阶段重跑

02E 会检查 02A–02D 的总结果。

重点检查：

```text
是否过度压缩
是否遗漏关键事件
是否对白太少
是否 OS 代替了戏剧冲突
是否缺少留白
是否不利于后续音频和分镜
```

如果 02E 输出 `needs_retry=true`，系统会按 `retry_stages` 从最早问题阶段开始重跑。

---

# JSON 修复机制

LLM 返回 JSON 解析失败时：

```text
json_repair.py 会把 broken_json 和错误原因发回 LLM
要求只修复 JSON 格式
再重新解析
```

该机制只修复格式，不新增业务内容。

---

# 最终硬规则校验

最终合并 `script.json` 后，`schema_validator.py` 会做程序级硬校验：

```text
顶层必要字段是否存在
segments 是否为空
segment_id 是否缺失或重复
segment type 是否合法
对白 segment 是否有 speaker
script_text 是否为空
audio_cues / storyboard_hints 是否引用真实 segment_id
event_coverage_map 是否为空
```

校验结果写入：

```text
schema_validation
quality_report.schema_validation_passed
quality_report.schema_validation_issues
```

---

# schema 1.0 顶层结构

```json
{
  "schema_version": "1.0",
  "module": "02_script_writer",
  "status": "success / needs_review",
  "stage_mode": "llm",
  "stage_status": [],
  "final_revision_rounds": [],
  "source": {},
  "script_id": "script_001",
  "title": "剧本标题",
  "format": "dialogue_os_blank",
  "adaptation_blueprint": {},
  "coverage_plan": [],
  "tone_plan": {},
  "compression_guardrails": {},
  "script_structure": {},
  "scene_beats": [],
  "event_coverage_map": [],
  "retention_design": {},
  "script": {},
  "segments": [],
  "script_text": "",
  "production_annotations": {},
  "audio_cues": [],
  "storyboard_hints": [],
  "risk_report": {},
  "evidence_index": [],
  "warnings": [],
  "revision_plan": {},
  "schema_validation": {},
  "quality_report": {}
}
```

---

# 最高原则

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

---

# 与后续模块的关系

```text
01_novel_parser → 02_script_writer → 06_storyboard / 08_audio
```

03/04/05 资产库系统可以与本模块并行或在本模块之后运行。

下游重点字段：

```text
06_storyboard：segments / scene_beats / storyboard_hints / event_coverage_map
08_audio：segments / script_text / audio_cues
10_final_assembly：script_text / retention_design / quality_report
```

---

# 测试建议

先完成 01 后，只跑 02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
```

完整跑 01→02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

运行前必须准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

并配置真实 LLM 环境变量。

---

# 显存释放

本模块会调用本地 LLM。

运行结束后必须执行：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

当前 `run_staged.py` 已经内置该释放逻辑。
