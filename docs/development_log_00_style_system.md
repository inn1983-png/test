# 00_style_system 风格圣经系统开发记录

## 本次改动

新增 `00_style_system`，作为全流程最前置的风格控制模块。

它的定位不是普通提示词，而是流水线硬依赖：后续 01–10 模块在 `configs/module_contracts.json` 中都能检查到风格相关产物，避免剧本、资产、分镜、图片、视频各自发挥导致风格污染。

## 新增模块

```text
00_style_system/
├─ module_config.json
├─ run_staged.py
└─ presets/
   └─ style_presets.json
```

## 输出产物

```text
style_bible.json              # 程序读取的结构化风格圣经
style_bible.md                # 人类可读风格说明
style_prompt_prefix.txt       # 01–06 文本 LLM 阶段可注入的风格前缀
image_style_lock.txt          # 07 图片生成阶段风格锁
video_style_lock.txt          # 09 视频生成阶段风格锁，短句，适配 LTX2.3
style_negative_prompt.txt     # 统一负向风格词
style_meta.json               # 风格系统元信息
```

## 内置风格预设

```text
ancient_live_action_realistic  # 古装真人写实短剧，默认
wuxia_live_action              # 武侠真人电影感
xianxia_cinematic              # 仙侠电影感
modern_urban_drama             # 现代都市真人短剧
republic_era_cinematic         # 民国电影感
chinese_3d_animation           # 中国风3D动画
ink_wash_motion                # 水墨国风动态绘本
```

切换方式：

```bash
set AI_DRAMA_STYLE_PRESET=wuxia_live_action
```

## 接入位置

`pipeline.json` 已升级为 00→10：

```text
00_style_system
01_novel_parser
02_script_writer
03_character_system
04_scene_system
05_prop_system
06_storyboard
07_storyboard_image
08_audio
09_video
10_final_assembly
```

`configs/module_contracts.json` 已加入风格依赖：

```text
01 依赖 style_bible.json
02–06 依赖 style_bible.json + style_prompt_prefix.txt
07 依赖 style_bible.json + image_style_lock.txt + style_negative_prompt.txt
08 依赖 style_bible.json
09 依赖 style_bible.json + video_style_lock.txt
10 依赖 style_bible.json
```

## 公共读取工具

新增：

```text
00_common/style_context.py
```

可读取：

```python
load_style_bible(run_dir)
load_style_prompt_prefix(run_dir)
load_image_style_lock(run_dir)
load_video_style_lock(run_dir)
load_style_negative_prompt(run_dir)
build_style_summary_for_llm(run_dir)
```

## 设计原则

```text
风格不是后期补丁，而是上游产物。
风格不是一句提示词，而是结构化约束。
图片阶段不重新发明风格，只继承 image_style_lock。
视频阶段不吃长风格解释，只继承 video_style_lock。
同一项目内所有资产、分镜图、视频段必须像同一套视觉系统。
```

## 后续建议

下一步应该把 `00_common/style_context.py` 逐步接入 02、03、04、05、06、07、09 的实际 stage_runner：

```text
02：剧本改编时注入 style_prompt_prefix，避免剧本层写出跨风格镜头。
03：角色卡生成时注入 style_bible，服装/妆容/材质服从风格。
04：场景卡生成时注入 style_bible，建筑/光影/时代服从风格。
05：道具卡生成时注入 style_bible，道具材质/时代一致。
06：分镜生成时注入 style_prompt_prefix，镜头语言服从风格。
07：图片任务构建时强制拼接 image_style_lock + style_negative_prompt。
09：LTX prompt 构建时强制拼接 video_style_lock。
```
