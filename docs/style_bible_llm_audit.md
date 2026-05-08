# 风格圣经 LLM 阶段接入检查

## 检查结论

本次检查对象：

```text
01_novel_parser
02_script_writer
03_character_system
04_scene_system
05_prop_system
06_storyboard
```

这些模块的真实 LLM 阶段都会调用各自 `core/llm_client.py` 的 `complete_json()`，并在 `complete_json()` 内统一调用：

```python
prompt_guard.apply_json_guard(system_prompt)
```

因此，本次把风格圣经注入点放在公共文件：

```text
00_common/llm_prompt_guard.py
```

这样所有 01–06 文本 LLM 阶段都会自动继承 `00_style_system` 的风格圣经，不需要逐个修改每个阶段 prompt 文件。

## 已确认的问题

之前的状态：

```text
configs/module_contracts.json 已经要求 01–06 依赖 00_style_system 输出。
但是 01–06 的 stage_runner.py 没有实际读取 style_context。
所以当时只是“合同依赖风格”，不是“prompt 真正注入风格”。
```

本次修复后：

```text
00_common/llm_prompt_guard.py 会读取 AI_DRAMA_RUN_DIR。
再通过 00_common/style_context.py 读取：
- style_prompt_prefix.txt
- style_bible.json 简要摘要
然后拼进所有 complete_json() 的 system prompt。
```

## 现在的注入链路

```text
00_style_system/run_staged.py
↓
生成 style_bible.json / style_prompt_prefix.txt
↓
configs/module_contracts.json 保证 00_style_system 先于 01–06 执行
↓
01–06 LLMClient.complete_json()
↓
00_common.llm_prompt_guard.apply_json_guard()
↓
00_common.style_context.load_style_prompt_prefix()
↓
STYLE_BIBLE 注入 system prompt
```

## 风格注入规则

注入内容包含：

```text
当前项目风格
核心风格
叙事气质
镜头语言
光影
色彩
风格继承规则
```

关键规则：

```text
不得自行切换时代体系、视觉风格、服装材质、场景美术、光影色彩或镜头语言。
角色、场景、道具、分镜、生产标注只能在 STYLE_BIBLE 允许的风格体系内描述。
如果原文风格与 STYLE_BIBLE 冲突，优先保持原作核心设定，再用 STYLE_BIBLE 统一视觉表达。
不要把完整风格圣经复制到最终 JSON 中。
```

## 覆盖范围

已覆盖：

```text
01 小说理解 / 段落标注 / 事件图谱 / 候选资产 / 生产预判 / 总检
02 剧本蓝图 / 结构 / 语音行 / 剧本草稿 / 生产标注 / 总检
03 角色合并 / 角色卡 / 角色绑定 / 角色质检 / 资产复核
04 场景合并 / 场景卡 / 场景绑定 / 场景质检 / 资产复核
05 道具合并 / 道具卡 / 道具绑定 / 道具质检 / 资产复核
06 资产闸门 / 分镜规划 / 单帧分镜 / 连续性绑定 / 总检
```

未直接覆盖但已有风格文件依赖：

```text
07_storyboard_image：不是 LLM_TEXT_PHASE，依赖 image_style_lock.txt 与 style_negative_prompt.txt。
09_video：不是文本 LLM 分阶段模块，依赖 video_style_lock.txt。
```

## 扩展风格库

风格预设支持多文件合并：

```text
00_style_system/presets/*.json
```

本次新增：

```text
00_style_system/presets/extra_style_presets.json
```

总风格数量：18 个。

## 后续建议

下一步应重点检查 07 和 09 的实际 prompt 构建代码：

```text
07：确认最终图片 positive prompt 是否强制拼接 image_style_lock.txt。
07：确认 final negative prompt 是否强制拼接 style_negative_prompt.txt。
09：确认 LTX prompt 是否强制拼接 video_style_lock.txt。
```

如果 07/09 只是合同依赖但没有实际拼接，也需要像 01–06 一样做运行时注入。
