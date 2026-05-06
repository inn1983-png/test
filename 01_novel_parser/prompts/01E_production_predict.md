# 01E 声音和视频生产预判阶段提示词

## 输入

- story_understanding
- story_spine
- event_graph
- paragraphs
- golden_lines 初稿

## 任务

不写正式剧本，只判断哪些原文信息适合变成旁白、对白、心理 OS、留白，以及哪些事件适合 6–12 秒视频单元。

必须输出：

```text
voice_line_candidates
video_unit_candidates
emotion_curve
golden_lines
confusion_risk_report
```

## 目标

提前服务 02 剧本、08 音频、09 视频，避免后面才发现台词太长、事件太挤、观众看不懂。
