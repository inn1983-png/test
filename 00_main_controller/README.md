# 00 总控系统

## 模块定位

00_main_controller 是整个小说转短剧/视频流水线的运行基座。

它不负责解析小说、写剧本、生图、配音或生视频，只负责：

```text
创建运行上下文
创建 project / book_chapter 运行目录
初始化 shared_assets / global_memory / manifest.json / artifacts.db / run_status.json
按 pipeline.json 顺序调用 01–10 子系统
把运行上下文环境变量传给每个模块
检查模块输入依赖
登记关键产物
支持 --from-module / --only-module / --dry-run
按阶段边界释放本地模型资源
校验 pipeline 配置
```

---

## 当前真实模块顺序

```text
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

当前关键产物：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
06_storyboard/storyboard.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
09_video/video_manifest.json
10_final_assembly/final.mp4
```

说明：01/02/03/04/05 已切换为真实分阶段 LLM 子系统，不再是 scaffold 占位输出；旧目录 `03_character_library / 04_scene_library / 05_prop_library` 不再使用。

---

## run.py / run_staged.py 入口规则

00 调用模块时使用 `00_common/module_runner.py`：

```text
如果模块目录存在 run_staged.py，优先运行 run_staged.py。
否则运行 run.py。
```

因此 01/02/03/04/05 使用真实 staged 入口，后续轻量模块仍可保留 run.py。

---

## 运行模式

### project 模式

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001
```

输出目录：

```text
workspace/projects/project_test_001/
```

### book_chapter 模式

```bash
python 00_main_controller/run_pipeline.py --mode book_chapter --book-id book_001 --chapter-id chapter_001
```

输出目录：

```text
workspace/books/book_001/chapters/chapter_001/
workspace/books/book_001/shared_assets/
workspace/books/book_001/global_memory/
```

---

## pipeline 校验

```bash
python 00_main_controller/validate_pipeline.py --pipeline pipeline.json --strict-order
```

`run_pipeline.py` 默认会先校验 pipeline。需要跳过时：

```bash
python 00_main_controller/run_pipeline.py --skip-validation
```

---

## 局部运行

从指定模块开始：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 03_character_system
```

只运行一个模块：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 05_prop_system
```

`--from-module` 和 `--only-module` 不能同时使用。

---

## dry-run 预演

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --dry-run
```

会打印运行目录、每个模块 input/output 路径、requires、produces，但不执行模块。

---

## 模块依赖检查

依赖配置：

```text
configs/module_contracts.json
```

00 在运行每个模块前会按三路查找上游产物：

```text
1. manifest.json 的 key_outputs
2. artifacts.db
3. workspace 中约定的模块输出路径
```

缺少上游产物时，模块会被标记为 blocked，不会盲跑。

---

## 本地 LLM JSON 护栏

统一文件：

```text
00_common/llm_prompt_guard.py
```

01/02/03/04/05 的 LLMClient 会自动：

```text
套用 Gemma JSON 输出护栏
要求只输出一个 JSON object
禁止 Markdown / 前言 / 后记 / 解释
在输入 payload 中加入 _local_model_output_contract 提醒模型不要复制
parse_json_from_text 后递归清理 analysis / reasoning / chain_of_thought / _local_model_output_contract 等内部字段
JSON repair 后也再次清理内部字段
```

---

## 本地模型资源释放阶段规则

资源管理统一文件：

```text
00_common/resource_manager.py
configs/local_resource_release.json
```

新规则：

```text
01–06：LLM_TEXT_PHASE，Gemma/本地 LLM 常驻，不在每个模块结束后主动卸载。
06 → 07：进入图片阶段前调用 release_llm_resources，释放 LLM 显存。
07：图片生成 / ComfyUI 阶段，完成后可释放图片模型资源。
08：TTS / CosyVoice2 阶段，按显存压力释放音频模型资源。
09：视频模型 LTX2.3 阶段，加载前释放其他大模型，完成后可释放视频资源。
10：普通合成阶段，默认不需要大模型卸载。
```

模块仍可在 finally 中调用：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

但对 01–06 来说，这个调用只做轻量 `gc.collect()`，不会主动清 CUDA，也不会执行 LLM 卸载命令。

阶段切换由 `run_pipeline.py` 统一处理：

```text
06_storyboard -> 07_storyboard_image：release_llm_resources()
07_storyboard_image -> 08_audio：release_image_resources()
08_audio -> 09_video：release_audio_resources() + release_image_resources()
09_video -> 10_final_assembly：release_video_resources()
```

外部卸载命令默认关闭，只有启用 `AI_DRAMA_ENABLE_RESOURCE_COMMANDS=1` 或配置 `enabled=true` 时才会执行。

---

## 运行状态记录

每次运行会生成：

```text
run_status.json
config_snapshot.json
```

记录模块状态：

```text
pending / running / success / failed / blocked / skipped
start_time / end_time / duration_seconds / return_code / message
```

config_snapshot.json 包含：

```text
timestamp：运行时间戳
platform：系统/Python 版本
run_args：命令行参数
selected_pipeline：实际执行的模块列表
pipeline_config：pipeline.json 原始配置
runtime_context：运行时上下文
env_snapshot：关键环境变量（API Key 脱敏）
```

---

## 自检命令

初始化 project 空流程：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id self_check_project --empty-pipeline
```

初始化 book_chapter 空流程：

```bash
python 00_main_controller/run_pipeline.py --mode book_chapter --book-id self_check_book --chapter-id chapter_001 --empty-pipeline
```

完整自检：

```bash
python 00_main_controller/self_check.py
```

---

## 运行上下文环境变量

每个模块运行时都会收到：

```text
AI_DRAMA_MODE
AI_DRAMA_RUN_ID
AI_DRAMA_RUN_DIR
AI_DRAMA_INPUT_DIR
AI_DRAMA_MODULE_NAME
AI_DRAMA_MODULE_INPUT_DIR
AI_DRAMA_MODULE_OUTPUT_DIR
AI_DRAMA_CONTEXT_PATH
AI_DRAMA_SHARED_ASSETS_DIR
AI_DRAMA_GLOBAL_MEMORY_DIR
```

模块不需要自己猜路径。

---

## 00 不做的事

00 不负责：

```text
小说解析
剧本改编
角色合并
场景标准化
道具标准化
分镜生成
生图
配音
生视频
成片拼接
```

这些必须交给对应模块。
