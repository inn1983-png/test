# 风格圣经流水线契约

## 核心原则

```text
UI 只传一个用户选择的 style_preset id。
00_style_system 只根据这个 id 生成当前项目唯一 STYLE_BIBLE。
后续 LLM / 图片 / 视频阶段不接收风格列表，也不接收多风格大包。
```

## 正确数据流

```text
Web UI 风格下拉框
↓
请求体只带：style_preset = "ancient_gritty_realism"
↓
后端环境变量：AI_DRAMA_STYLE_PRESET = ancient_gritty_realism
↓
00_style_system 输出当前项目唯一风格圣经
↓
01–06 文本 LLM 阶段：读取 style_prompt_prefix.txt
↓
07 图片阶段：读取 image_style_lock.txt + style_negative_prompt.txt
↓
09 视频阶段：读取 video_style_lock.txt + style_negative_prompt.txt
```

## 禁止事项

```text
禁止把全部风格预设列表传给 LLM。
禁止把 preset id 当作图片提示词或 LTX 提示词直接拼进去。
禁止 02–06 阶段自行切换时代、画风、光影、服装、场景美术。
禁止 07 图片阶段脱离 image_style_lock 自己发挥风格。
禁止 09 LTX 阶段脱离 video_style_lock 自己发挥风格。
```

## 关键文件

```text
00_style_system/run_staged.py                 # 选择一个 preset，生成 STYLE_BIBLE
00_style_system/presets/*.json                # 多文件风格库，仅供 00_style_system 选择
00_common/style_context.py                    # 风格读取工具
00_common/llm_prompt_guard.py                 # 01–06 LLM 前置注入
07_storyboard_image/core/prompt_builder.py    # 07 图片 prompt 风格注入
00_main_controller/sitecustomize.py           # 09 视频 prompt 运行时风格 hook
web_ui/static/style_picker.js                 # UI 风格选择，仅传一个 preset id
```

## 一键自检

先运行风格系统：

```bash
set AI_DRAMA_STYLE_PRESET=ancient_gritty_realism
python 00_main_controller/run_pipeline.py --only-module 00_style_system --project-id style_test
```

再检查风格链路：

```bash
python 00_style_system/check_style_chain.py --run-dir workspace/projects/style_test
```

通过时应该看到：

```text
status: passed
style_bible_loaded: true
prompt_prefix_loaded: true
image_style_lock_loaded: true
video_style_lock_loaded: true
style_negative_prompt_loaded: true
```

## 当前兼容说明

`web_ui/static/style_picker.js` 为兼容旧后端，会同时写入：

```json
{
  "style_preset": "ancient_gritty_realism",
  "image_style_suffix": "ancient_gritty_realism"
}
```

但 `image_style_suffix` 里仍然只是一个 preset id，不是风格描述，不是风格列表。

`07_storyboard_image/core/prompt_builder.py` 已经做了防误拼：如果 `AI_DRAMA_IMAGE_STYLE_SUFFIX` 看起来只是 preset id，就不会把它当成图片提示词拼进 prompt。

后续如果正式修改 `web_ui/server.py`，应直接把：

```text
style_preset → AI_DRAMA_STYLE_PRESET
```

作为唯一后端映射，然后删除兼容桥。
