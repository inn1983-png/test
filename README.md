# AI Short Drama Modular System

这是一个用于“小说 → 剧本 → 角色库/场景库/道具库 → 分镜 → 分镜图 → 音频 → 视频 → 成片”的模块化项目骨架。

## 核心设计

- 一个文件夹就是一个独立系统。
- 每个系统只做一件事。
- 所有系统共用根目录依赖。
- 每个系统都有自己的 `input/`、`output/`、`prompt.md`、`rules.md`、`module_config.json`、`run.py`。
- 最后由 `00_main_controller/` 按 `pipeline.json` 组合调用。

## 目录结构

```text
AI_ShortDrama_System/
├─ 00_main_controller/          # 总控系统
├─ 00_common/                   # 公共工具、统一读写、数据协议
├─ 01_novel_parser/             # 小说解析系统
├─ 02_script_writer/            # 剧本改编系统
├─ 03_character_library/        # 角色库系统
├─ 04_scene_library/            # 场景库系统
├─ 05_prop_library/             # 道具库系统
├─ 06_storyboard/               # 分镜系统
├─ 07_storyboard_image/         # 分镜图生成系统
├─ 08_audio/                    # 音频系统
├─ 09_video/                    # 视频生成系统
└─ 10_final_assembly/           # 成片拼接系统
```

## 运行方式

先安装共用依赖：

```bash
pip install -r requirements.txt
```

运行完整流水线：

```bash
python 00_main_controller/run_pipeline.py
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