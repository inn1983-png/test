# 02 失败样本目录

本目录用于保存 02_script_writer 真实测试中出现的问题样本。

建议每个失败样本单独建一个子目录：

```text
failure_cases/
  2026-xx-xx_over_compression_case_001/
    input_summary.md
    novel_analysis_excerpt.json
    script_output.json
    problem_report.md
```

---

# problem_report.md 建议格式

```text
# 失败类型

# 失败表现

# 相关输出字段

# 判断原因

# 希望如何修复

# 复测结果
```

---

# 典型失败类型

```text
over_compression
 dialogue_weak
 os_overuse
 voice_line_too_long
 visual_abstract
 too_many_characters
 continuity_weak
 source_line_lost
 character_name_drift
 tts_unreadable
 episode_split_wrong
 version_selection_wrong
```
