# 02 剧本改编系统测试清单

本目录用于记录 02_script_writer 的真实测试结果。

---

# 测试前置

必须先完成 01，并生成：

```text
01_novel_parser/novel_analysis.json
```

必须配置真实 LLM：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

---

# 推荐测试命令

只跑 02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
```

跑 01→02：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

---

# 核心检查项

## 1. 基础结构

```text
script.json 是否存在
script.txt 是否存在
script_meta.json 是否存在
intermediate/02A-02F 是否全部存在
schema_validation.passed 是否为 true
quality_report.needs_review 是否为 false
```

## 2. 剧本质量

```text
是否过度压缩
是否保留关键事件
是否有足够对白冲突
OS 是否过多
是否有留白
是否继承 golden_lines / 高刺激句
```

## 3. 音频驱动

```text
voice_line_plan 是否完整
voice_line_type 是否只有 N/D/M/S
N/D/M 是否有 tts_text
D 是否有 speaker
是否存在超过 12 秒的 voice_line
script_text 是否包含音频行标记
```

## 4. 单帧分镜准备

```text
visual_dramatic_units 是否有 action_chain
continuity_in / continuity_out 是否清楚
continuity_chain 是否完整
character_load_report 是否标记多人风险
visual_executability_report 是否标记抽象画面
```

## 5. 多版本与分集

```text
episode_split_plan 是否合理
script_versions 是否至少两个
selected_version_id 是否存在于 script_versions
selection_reason 是否清楚
script_emotion_curve 是否有起伏
```

---

# 失败样本

如果真实测试失败，把样本放入：

```text
02_script_writer/tests/failure_cases/
```

并把共性修复策略写入：

```text
02_script_writer/prompt_tuning_notes.md
```
