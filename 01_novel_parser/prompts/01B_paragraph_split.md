# 01B 段落切分阶段提示词

## 输入

- 完整 novel.txt

## 任务

只做章节识别、段落切分、timeline 初步标记。

不得总结全文，不得改写，不得写剧本。

必须输出：

```text
chapters
paragraphs
timeline
```

每个 paragraph 必须有：

```text
paragraph_id
chapter_id
index
text
start_char
end_char
paragraph_type
```

后续所有事件、候选、金句、证据都必须回到 paragraph_id。
