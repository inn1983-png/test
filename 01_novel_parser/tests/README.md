# 01 小说解析系统测试清单

## 前置配置

必须配置本地 OpenAI 兼容 LLM：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

## 测试 1：缺少 LLM 配置必须失败

不配置上述环境变量时运行 01，应该失败。

## 测试 2：缺少 novel.txt 必须失败

`input/novel.txt` 为空或不存在时，01 应该失败。

## 测试 3：单模块真实运行

准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

运行：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
```

应生成：

```text
workspace/projects/project_test_001/01_novel_parser/novel_analysis.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01A_story_understanding.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01B_paragraphs.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01C_event_graph.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01D_candidates.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01E_production_predict.json
workspace/projects/project_test_001/01_novel_parser/intermediate/01F_quality_check.json
```

## 测试 4：检查最终 JSON

`novel_analysis.json` 应包含：

```text
stage_mode=llm
stage_status
schema_validation
quality_report.stage_scores
story_understanding
story_spine
paragraphs
event_graph
candidate_characters
candidate_scenes
candidate_props
voice_line_candidates
video_unit_candidates
evidence_index
```

## 测试 5：检查候选提取

文章中出现过的人、地点、物件都应该进入候选。

候选过多不是错误。
遗漏才是错误。
