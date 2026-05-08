# AI Short Drama Modular System

这是一个用于“风格圣经 → 小说 → 剧本 → 角色库/场景库/道具库 → 分镜 → 分镜图 → 音频 → 视频 → 成片”的模块化项目骨架。

## 核心设计

- 一个文件夹就是一个独立系统。
- 每个系统只做一件事。
- 所有系统共用根目录依赖。
- 每个系统都有自己的 `input/`、`output/`、`module_config.json`、`run.py` 或 `run_staged.py`。
- 最后由 `00_main_controller/` 按 `pipeline.json` 组合调用。
- `00_style_system/` 是全流程前置风格系统，负责生成统一风格圣经，后续模块通过契约强制继承。

## 目录结构

```text
AI_ShortDrama_System/
├─ 00_style_system/             # 风格圣经系统：全局风格锁、多风格预设、图片/视频风格锁
├─ 00_main_controller/          # 总控系统
├─ 00_common/                   # 公共工具、统一读写、数据协议
├─ 01_novel_parser/             # 小说解析系统
├─ 02_script_writer/            # 剧本改编系统
├─ 03_character_system/         # 角色系统
├─ 04_scene_system/             # 场景系统
├─ 05_prop_system/              # 道具系统
├─ 06_storyboard/               # 分镜系统
├─ 07_storyboard_image/         # 分镜图生成系统
├─ 08_audio/                    # 音频系统
├─ 09_video/                    # 视频生成系统
└─ 10_final_assembly/           # 成片拼接系统
```

## 风格圣经系统

`00_style_system` 会在流水线最前面生成以下关键产物：

```text
00_style_system/style_bible.json
00_style_system/style_bible.md
00_style_system/style_prompt_prefix.txt
00_style_system/image_style_lock.txt
00_style_system/video_style_lock.txt
00_style_system/style_negative_prompt.txt
00_style_system/style_meta.json
```

这些产物已经写入 `configs/module_contracts.json`，后续模块会把风格文件作为必需上游产物。这样风格不是一句提示词建议，而是流水线硬依赖。

风格预设支持多文件合并：

```text
00_style_system/presets/*.json
```

只要 JSON 文件里包含 `presets` 字段，`00_style_system/run_staged.py` 会自动合并。

当前内置风格预设：

```text
ancient_live_action_realistic  # 古装真人写实短剧，默认
ancient_gritty_realism         # 古代粗粝现实主义
ancient_palace_drama           # 古装宫廷权谋剧
ancient_war_epic               # 古代战争史诗
song_dynasty_slice_of_life     # 宋韵市井生活剧
tang_dynasty_romance           # 盛唐华丽爱情剧
ming_qing_mystery              # 明清探案悬疑剧
wuxia_live_action              # 武侠真人电影感
xianxia_cinematic              # 仙侠电影感
dark_fantasy_chinese           # 东方暗黑奇幻
modern_urban_drama             # 现代都市真人短剧
modern_suspense_thriller       # 现代悬疑冷峻短剧
modern_romance_idol            # 现代偶像甜宠短剧
republic_era_cinematic         # 民国电影感
cyberpunk_noir                 # 赛博朋克冷色 noir
chinese_3d_animation           # 中国风3D动画
claymation_chinese_folk        # 中国民俗黏土动画
ink_wash_motion                # 水墨国风动态绘本
```

切换风格：

```bash
set AI_DRAMA_STYLE_PRESET=ancient_gritty_realism
```

或任意替换为上面的 preset id。

公共读取工具：

```text
00_common/style_context.py
```

后续模块可通过它读取：

```python
style_bible = style_context.load_style_bible(run_dir)
style_prefix = style_context.load_style_prompt_prefix(run_dir)
image_style_lock = style_context.load_image_style_lock(run_dir)
video_style_lock = style_context.load_video_style_lock(run_dir)
negative_prompt = style_context.load_style_negative_prompt(run_dir)
```

## 01–06 LLM 阶段风格注入

`00_common/llm_prompt_guard.py` 已经接入 `00_common/style_context.py`。

所有 01–06 文本 LLM 阶段在调用 `complete_json()` 时，都会经过 `prompt_guard.apply_json_guard()`，因此会自动注入：

```text
00_style_system/style_prompt_prefix.txt
00_style_system/style_bible.json 的简要摘要
```

这意味着 01–06 不只是合同依赖风格文件，而是在实际 LLM system prompt 里继承风格圣经。

## 运行方式

先安装共用依赖：

```bash
pip install -r requirements.txt
```

运行完整流水线：

```bash
python 00_main_controller/run_pipeline.py
```

只运行风格系统：

```bash
python 00_main_controller/run_pipeline.py --only-module 00_style_system
```

运行单个模块：

```bash
python 02_script_writer/run.py
```

## 开发原则

1. 不把所有功能塞进一个大工作流。
2. 每个模块输入输出必须标准化。
3. 哪个模块不好，就只改哪个文件夹。
4. 视频生成只负责“动起来”，不要承担剧情理解。
5. 剧本、角色库、分镜图质量优先于全自动。
6. 风格控制必须从 `00_style_system` 开始，不允许后续模块自行切换画风、时代体系、材质体系和镜头语言。
