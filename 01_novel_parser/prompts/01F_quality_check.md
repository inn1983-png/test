# 01F 汇总校验阶段提示词

## 输入

- 01A–01E 的全部中间结果
- paragraphs
- 原文 novel.txt

## 任务

检查遗漏、矛盾、误读、JSON 缺字段、证据不足。

必须输出：

```text
evidence_index
quality_report
warnings
chapter_memory_update
最终缺漏检查结论
```

## 重点检查

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
