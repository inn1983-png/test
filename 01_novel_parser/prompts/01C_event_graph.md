# 01C 事件图谱阶段提示词

## 输入

- story_understanding
- story_spine
- paragraphs

## 任务

只提取事件、因果关系、冲突、高留存片段、场戏价值、人物弧光。

不得提取全量资产候选，不得写剧本，不得生成分镜。

必须输出：

```text
event_graph
conflicts
high_retention_segments
scene_value_map
character_arc_map
```

事件之间必须标记：

```text
因果
推进
反转
铺垫
回忆
插叙
并行支线
```
