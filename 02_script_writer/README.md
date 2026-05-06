# 02 剧本改编系统

## 模块定位

02 剧本改编系统负责把 01 小说解析结果改编为适合短视频 / 横屏短剧 / AI 漫剧生产的正式剧本。

当前 02 的定位已经升级为：

```text
音频驱动 + 单帧分镜友好 + 防压缩过狠 + 多版本评估 + 失败样本回灌 的真实 LLM 剧本改编子系统
```

边界必须清楚：

```text
02 负责：剧本改编、对白、OS、留白、动作、情绪、语音行预拆分、剧本生产标注、单帧分镜准备字段、剧本质量评估。
02 不负责：角色资产库、场景资产库、道具资产库、正式分镜、图片生成、视频生成、ComfyUI 调用。
```

02E 中的 `visual_dramatic_units` / `storyboard_hints` / `continuity_chain` 只是剧本层面的动作链、画面锚点和连续性提示，方便 06 分镜系统继续拆单帧，不是正式分镜，也不是图像提示词。

---

# 当前理论完成状态

02 当前已完成 schema 1.2 理论架构搭建：

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

后续需要根据真实小说解析结果和本地模型表现继续精修 prompt、评分阈值、剧本长度控制、对白质量、语音行时长估计和单帧连续性字段。

---

# 当前实际运行入口

00 总控会优先运行模块内的：

```text
run_staged.py
```

因此 02 当前正式 pipeline 入口是：

```text
02_script_writer/run_staged.py
```

旧的 `run.py` 仍是 scaffold 占位入口，但正式流程应使用 `run_staged.py`。

---

# 02 必须真实调用 LLM

02 不再支持 scaffold 占位剧本作为正式结果。

凡是 02A–02F 需要改编、结构设计、语音行拆分、剧本生成、标注、评分的步骤，都必须真实调用 LLM。

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
  prompt_tuning_notes.md
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
    02C_voice_line_plan.md
    02D_script_draft.md
    02E_production_annotations.md
    02F_quality_check.md
  tests/
    README.md
    failure_cases/
      README.md
```

运行后会生成：

```text
intermediate/02A_adaptation_blueprint.json
intermediate/02B_script_structure.json
intermediate/02C_voice_line_plan.json
intermediate/02D_script_draft.json
intermediate/02E_production_annotations.json
intermediate/02F_quality_check.json
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
candidate_characters
candidate_scenes
candidate_props
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
script.txt        # 可读剧本文本，包含音频行标记
script_meta.json  # 阶段状态、评分、重跑记录、schema 校验
```

---

# 02A–02F 分阶段工作流

## 02A：改编蓝图阶段

输出：

```text
adaptation_blueprint
coverage_plan
tone_plan
compression_guardrails
length_strategy
episode_split_plan
script_version_strategy
```

目标：先决定怎么改，明确保留哪些关键事件和冲突，防止长文案被强行压成固定 2 分钟，并决定是否需要拆集/拆段。

## 02B：剧本结构阶段

输出：

```text
script_structure
scene_beats
event_coverage_map
character_name_usage
retention_design
script_emotion_curve
```

目标：把故事拆成可写剧本的节拍，明确每个事件被哪个 beat 覆盖，锁定角色称呼一致性，并规划情绪曲线。

## 02C：语音行预拆分阶段

输出：

```text
voice_line_plan
script_video_unit_candidates
duration_risk_report
```

语音行类型：

```text
N：旁白，固定旁白音色，弱情绪
D：角色对白，角色音色，保留较强情绪，可用于口型
M：心理 OS，角色音色，中等情绪，不强制口型
S：静音留白
```

02C 的目标是提前适配 08_audio 和后续视频单元：

```text
一个 voice_line + 一个主场景 + 一个连续动作链 + 一个末帧承接 + 6-12 秒视频段
```

如果语音行或候选视频单元超过 12 秒，02C 必须标记 `needs_split` 并给出拆分建议。

## 02D：正式剧本阶段

输出：

```text
script
script_versions
selected_version_id
selection_reason
segments
script_text
source_line_usage
tts_readability_report
```

02D 至少生成两个版本，例如：

```text
faithful_source
high_conflict_short_drama
audio_driven_balanced
```

最终 `segments` 必须来自 `selected_version_id` 对应版本。

## 02E：剧本生产标注阶段

输出：

```text
production_annotations
audio_cues
visual_dramatic_units
storyboard_hints
visual_executability_report
character_load_report
continuity_chain
risk_report
```

说明：02E 只做剧本标注，不生成正式分镜、不生成图像提示词、不生成视频提示词。

单帧分镜策略：

```text
单帧 = 生产单位
四宫格 = 后续连续性预览 / 检查单位
```

## 02F：总检评分阶段

输出：

```text
quality_report
evidence_index
warnings
revision_plan
failure_learning_notes
```

02F 重点检查：

```text
是否过度压缩
是否遗漏关键事件
是否对白太少
是否 OS 代替戏剧冲突
是否缺少留白
是否存在 12 秒风险
是否继承 01 golden_lines / 高刺激原文句子
角色称呼是否稳定
分集/分段是否合理
多版本生成和选择是否合理
情绪曲线是否有起伏
口播/TTS 是否顺畅
画面动作是否可执行
单帧人物数量是否可控
连续性链表是否清晰
是否输出失败样本回灌建议
```

如果发现问题，会输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["02C"],
    "revision_instructions": []
  }
}
```

`stage_runner.py` 会从最早需要重跑的阶段开始，连同后续阶段再执行一轮。

---

# 评分与重跑机制

02 有两层修正机制。

## 第一层：阶段内评分重跑

每个阶段生成后，`quality_checker.py` 会检查：

```text
必要字段是否存在
02A 是否有 length_strategy / episode_split_plan / script_version_strategy
02B 是否有 character_name_usage / script_emotion_curve
02C 是否有 voice_line_plan / script_video_unit_candidates / 12 秒风险标记
02D 是否有 script_versions / selected_version_id / segments / voice_line_id / source_line_usage / tts_readability_report
02E 是否有 audio_cues / visual_dramatic_units / storyboard_hints / visual_executability_report / character_load_report / continuity_chain
02F 是否有 failure_learning_notes 或要求重跑
```

如果分数低于阈值，会生成：

```text
revision_instructions
```

然后把修改意见传回同一阶段，让 LLM 重新执行。

## 第二层：02F 总检触发阶段重跑

02F 会检查 02A–02E 的总结果。

如果 02F 输出 `needs_retry=true`，系统会按 `retry_stages` 从最早问题阶段开始重跑。

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
voice_line_plan 是否为空
voice_line_id 是否缺失或重复
voice_line_type 是否只能为 N/D/M/S
D 类型 voice_line 是否有 speaker
N/D/M 是否有 tts_text
voice_line / video_unit 是否超过 12 秒
segments 是否为空
segment_id 是否缺失或重复
segment type 是否合法
对白 segment 是否有 speaker
segment 是否绑定真实 voice_line_id
script_versions 是否为空
selected_version_id 是否存在于 script_versions
script_text 是否为空
audio_cues / storyboard_hints / visual_dramatic_units 是否引用真实 segment_id / voice_line_id
event_coverage_map 是否为空
source_line_usage 是否为空
character_name_usage 是否为空
episode_split_plan 是否为空
script_emotion_curve 是否为空
continuity_chain 是否引用真实 visual_unit_id
failure_learning_notes 是否为空
tts_readability_report / visual_executability_report / character_load_report 是否为空
```

---

# schema 1.2 顶层结构

```json
{
  "schema_version": "1.2",
  "module": "02_script_writer",
  "status": "success / needs_review",
  "stage_mode": "llm",
  "stage_status": [],
  "final_revision_rounds": [],
  "source": {},
  "script_id": "script_001",
  "title": "剧本标题",
  "format": "audio_driven_dialogue_os_blank_single_frame_ready",
  "adaptation_blueprint": {},
  "coverage_plan": [],
  "tone_plan": {},
  "compression_guardrails": {},
  "length_strategy": {},
  "episode_split_plan": [],
  "script_version_strategy": {},
  "script_structure": {},
  "scene_beats": [],
  "event_coverage_map": [],
  "retention_design": {},
  "character_name_usage": [],
  "script_emotion_curve": [],
  "voice_line_plan": [],
  "script_video_unit_candidates": [],
  "duration_risk_report": {},
  "script": {},
  "script_versions": [],
  "selected_version_id": "",
  "selection_reason": "",
  "segments": [],
  "script_text": "",
  "source_line_usage": [],
  "tts_readability_report": {},
  "production_annotations": {},
  "audio_cues": [],
  "visual_dramatic_units": [],
  "storyboard_hints": [],
  "visual_executability_report": {},
  "character_load_report": {},
  "continuity_chain": [],
  "risk_report": {},
  "evidence_index": [],
  "warnings": [],
  "revision_plan": {},
  "failure_learning_notes": [],
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
N/D/M/S 语音行预拆分
剧本层面的音频提示
剧本层面的单帧分镜动作链和连续性提示
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
06_storyboard：segments / scene_beats / visual_dramatic_units / storyboard_hints / event_coverage_map / character_name_usage / continuity_chain
08_audio：voice_line_plan / segments / script_text / audio_cues / tts_readability_report
09_video：script_video_unit_candidates / duration_risk_report / visual_dramatic_units / character_load_report
10_final_assembly：script_text / retention_design / quality_report
后续测试精修：failure_learning_notes / prompt_tuning_notes.md / tests/failure_cases
```

---

# 失败样本回灌

真实测试后，把失败样本记录到：

```text
02_script_writer/tests/failure_cases/
```

并把共性修复规则写入：

```text
02_script_writer/prompt_tuning_notes.md
```

02F 会输出 `failure_learning_notes`，用于提示后续应该记录哪些失败类型和修复方向。

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
