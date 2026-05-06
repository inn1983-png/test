# 02 剧本改编系统 Prompt 精修记录

本文档用于记录 02 在真实测试中出现的失败类型、原因判断和后续 prompt 修复策略。

---

# 使用规则

1. 只有真实测试中反复出现的问题才写入这里。
2. 不记录一次性偶发错误。
3. 每条记录必须包含：失败类型、表现、可能原因、修复策略、验证样本。
4. 如果 02F 输出了 `failure_learning_notes`，可以把其中有价值的内容整理到本文档。
5. 修改 prompt 后，应在本文件补充修改日期和验证结果。

---

# 常见失败类型

```text
over_compression          剧本压缩过狠
 dialogue_weak             对白弱，冲突不足
 os_overuse                OS 过多，像解说不是短剧
 voice_line_too_long       单条语音行过长，后续视频单元超过 12 秒
 visual_abstract           画面动作抽象，不利于单帧分镜
 too_many_characters       单帧人物过多，后续生图容易崩
 continuity_weak           前后单帧连续性不足
 source_line_lost          原文高刺激句 / golden_lines 丢失
 character_name_drift      角色称呼漂移，污染后续角色库 / 分镜
 tts_unreadable            句子不适合 TTS 或 1.1 倍速口播
 episode_split_wrong       分集 / 分段不合理
 version_selection_wrong   多版本选择不合理
```

---

# 记录模板

```text
## YYYY-MM-DD｜失败类型

### 测试样本
- 项目 / 章节：
- 输入长度：
- 使用模型：

### 失败表现

### 可能原因

### 修复策略

### 修改的文件

### 复测结果
```
