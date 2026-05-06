# 01D 全量候选提取阶段提示词

## 输入

- paragraphs
- event_graph
- candidate_extraction_policy

## 任务

只提取文章里提到过的全部人、地点、物件。

不得筛选，不得压缩，不得最终合并，不得写剧本。

必须输出：

```text
candidate_characters
candidate_scenes
candidate_props
asset_binding_hints
visual_risk_report
```

## 最高规则

只要文章里提到过的人、地点、物件，都必须作为候选输出。

不确定也要输出，confidence 可以低，并在 risk_notes 写明原因。

importance 只表示后续优先级，不能作为是否提取的门槛。
