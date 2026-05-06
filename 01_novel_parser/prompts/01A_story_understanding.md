# 01A 全文理解阶段提示词

## 输入

- 完整 novel.txt

## 任务

只做全文理解，不写剧本，不提取全量角色/场景/道具候选，不生成分镜。

必须输出：

```text
story_understanding
story_spine
viewer_experience_plan
information_reveal_plan
adaptation_strategy
misread_prevention
```

## 最高规则

先判断这篇到底讲什么，再判断主角是谁、主线是什么、核心矛盾是什么、哪些信息不能提前揭露。

不得只抓局部爆点误读全文。
