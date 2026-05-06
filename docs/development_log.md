# 开发记录与协作规则

本文档记录每一轮框架改动，方便用户、新对话、本地 Codex 接手。

---

# 协作规则

1. 每一轮改动前，先简要说明准备做什么。
2. 用户可以随时补充要求。
3. 每一轮重要改动后，必须写入 README 或 docs 文档。
4. 不只改代码，也要同步更新说明。
5. 每个模块必须说明：
   - 模块定位
   - 输入
   - 输出
   - 与其他模块关系
   - 清理规则
   - 是否使用本地模型
   - 是否需要释放显存
6. 00 总控层的改动必须优先写清楚，因为它决定所有后续模块的运行方式。
7. 后续采用连续开发模式：在用户给出明确方向后，可以连续修改代码和文档，不需要每一个小改动都反复询问确认。
8. 需要提前确认的情况仅限：删除大量文件、重构核心架构、改变模块边界、修改已确定的数据目录规则、可能破坏现有可运行流程的改动。
9. 每一轮完成后，必须总结本轮具体做了什么、修改了哪些文件、下一步建议做什么。

---

# 当前开发阶段

当前阶段：00 + 01–10 子系统框架已能闭环，建议用户先一次性测试，再逐步精细打磨每一步。

当前框架已经覆盖：

```text
短篇 / 长篇运行目录
长篇 shared_assets / global_memory 初始化
runtime_context.json
manifest.json
artifacts.db
run_status.json
pipeline 校验
模块调度
模块输入依赖检查
局部运行 --from-module / --only-module
dry-run 预演模式
显存 / 本地资源释放入口
安全清理
产物查询
空流程自检
01–10 框架关键产物输出
01–10 完整框架闭环自检
```

建议用户在本地执行：

```bash
python 00_main_controller/self_check.py
```

如果通过，再执行真实项目测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001
```

---

# 已完成改动

## 2026-05-07：初始化模块化总框架

完成内容：

- 创建 00–10 模块目录
- 创建总 README
- 创建 `pipeline.json`
- 创建 `requirements.txt`
- 创建 `.gitignore`
- 创建 `.env.example`
- 创建 00_common 公共工具层
- 为每个模块创建基础 `run.py`
- 为每个模块加入资源释放逻辑

## 2026-05-07：补充模块说明文档

完成内容：

- 新增 `docs/codex_handoff.md`
- 新增 `docs/module_isolation.md`
- 新增 `docs/project_workspace.md`
- 新增 01–10 各模块 README

核心规则：

```text
一个文件夹 = 一个独立子系统
模块代码和运行数据分离
长篇小说使用 shared_assets 共享资产库
每个本地模型模块跑完必须释放显存
```

## 2026-05-07：开始打磨 00 总控基座

完成内容：

- 新增 `00_common/workspace_manager.py`
- 支持短篇项目模式：`workspace/projects/{project_id}/`
- 支持长篇章节模式：`workspace/books/{book_id}/chapters/{chapter_id}/`
- 长篇模式自动创建共享资产库：`shared_assets/`
- 长篇模式自动创建全书记忆：`global_memory/`
- 更新 `00_common/module_runner.py`，可以把运行上下文传给每个模块
- 更新 `00_main_controller/run_pipeline.py`，支持 `--mode project` 和 `--mode book_chapter`

## 2026-05-07：产物索引从 manifest.json 升级为 SQLite + 轻量 manifest

原因：

长篇项目会生成大量图片、音频、视频。如果所有产物都写入一个 `manifest.json`，文件会越来越大，不适合长期使用。

完成内容：

- 新增 `00_common/artifact_db.py`
- 更新 `00_common/artifact_registry.py`
- 新增 `00_common/artifact_resolver.py`
- 新增 `docs/artifact_storage.md`

当前规则：

```text
manifest.json = 轻量摘要 + 关键输出索引
artifacts.db = 全部产物详细记录
artifact_resolver.py = 后续模块查找资产的统一工具
```

## 2026-05-07：完善 00 总控说明、清理工具、产物查询工具

完成内容：

- 新增 `00_main_controller/README.md`
- 新增 `00_main_controller/cleanup_workspace.py`
- 新增 `00_main_controller/query_artifacts.py`
- 更新 `00_common/workspace_manager.py`，初始化运行目录时同步创建 `runtime_context.json`、`manifest.json`、`artifacts.db`
- 更新 `00_main_controller/README.md`，写入运行命令、清理命令、产物查询命令

新增能力：

```text
安全删除短篇项目：
python 00_main_controller/cleanup_workspace.py project --project-id project_test_001 --yes

安全删除长篇某章，保留共享资产：
python 00_main_controller/cleanup_workspace.py chapter --book-id book_001 --chapter-id chapter_001 --yes

查询关键输出：
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001 --keys

查询全部产物：
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001
```

## 2026-05-07：继续打磨 00 总控基座：资源释放配置 + 空流程自检

完成内容：

- 更新 `00_common/resource_manager.py`
- 新增 `configs/local_resource_release.json`
- 更新 `00_main_controller/run_pipeline.py`
- 新增 `00_main_controller/self_check.py`
- 更新 `00_main_controller/README.md`

新增能力：

```text
1. 本地资源释放命令配置
2. 外部释放命令默认关闭，避免误停 ComfyUI / 本地 LLM / TTS 等服务
3. 支持 AI_DRAMA_ENABLE_RESOURCE_COMMANDS=1 显式启用释放命令
4. 支持 AI_DRAMA_RESOURCE_RELEASE_CONFIG 指定释放配置文件
5. 支持 run_pipeline.py --empty-pipeline 只初始化运行上下文和产物索引
6. 支持 self_check.py 一键检查 00 总控基座
```

## 2026-05-07：00 总控最后一轮补强：状态、局部运行、依赖检查、dry-run

完成内容：

- 新增 `00_common/run_status.py`
- 新增 `00_common/module_contracts.py`
- 新增 `configs/module_contracts.json`
- 更新 `00_common/module_runner.py`
- 更新 `00_main_controller/run_pipeline.py`
- 更新 `00_main_controller/self_check.py`
- 更新 `00_main_controller/README.md`

新增能力：

```text
1. 每次运行生成 run_status.json
2. 每个模块记录 pending / running / success / failed / blocked / skipped
3. 记录 start_time / end_time / duration_seconds / return_code / message
4. 支持 --from-module 从指定模块继续跑
5. 支持 --only-module 只跑一个模块
6. 支持 --dry-run 只预演运行计划，不执行模块
7. 支持 configs/module_contracts.json 声明模块 requires / produces
8. 运行模块前检查上游关键产物是否存在
9. 支持 --skip-dependency-check 临时跳过依赖检查
10. self_check.py 增加 run_status.json 和 dry-run 检查
```

## 2026-05-07：01–10 子系统框架闭环

完成内容：

- 更新 `00_common/base_module.py`，支持关键产物写入并登记到 `manifest.key_outputs`
- 更新 `01_novel_parser/run.py`
- 更新 `02_script_writer/run.py`
- 更新 `03_character_library/run.py`
- 更新 `04_scene_library/run.py`
- 更新 `05_prop_library/run.py`
- 更新 `06_storyboard/run.py`
- 更新 `07_storyboard_image/run.py`
- 更新 `08_audio/run.py`
- 更新 `09_video/run.py`
- 更新 `10_final_assembly/run.py`
- 更新 `00_main_controller/self_check.py`
- 更新 `00_main_controller/README.md`

新增能力：

```text
1. 01 输出 novel_analysis.json
2. 02 输出 script.json
3. 03 输出 characters.json
4. 04 输出 scenes.json
5. 05 输出 props.json
6. 06 输出 storyboard.json
7. 07 输出 image_manifest.json，并生成占位 shot_001.png
8. 08 输出 final_audio.wav，并生成 audio_manifest.json
9. 09 输出 video_manifest.json，并生成占位 clip_001.mp4
10. 10 输出 final.mp4，并生成 assembly_manifest.json
11. 所有关键产物登记到 manifest.key_outputs 和 artifacts.db
12. self_check.py 会完整跑一次 project 模式 01–10 框架流程
13. self_check.py 会检查 01–10 关键产物、manifest 登记、run_status success
```

重要说明：

```text
当前 01–10 输出的是 scaffold 占位产物，不是真实 AI 生成结果。
目的是先让完整系统可运行、可查询、可清理、可自检。
后续再逐步精修每一步真实业务逻辑。
```

## 2026-05-07：记录连续开发协作偏好

完成内容：

- 更新 `docs/development_log.md`
- 明确后续采用连续开发模式
- 明确何时不需要用户逐步确认
- 明确何时必须先确认

新增规则：

```text
用户给出明确方向后，可以连续修改代码和文档。
不需要每一个小改动都反复询问确认。
删除大量文件、重构核心架构、改变模块边界、修改数据目录规则、可能破坏现有可运行流程时，需要先确认。
每轮完成后必须总结做了什么、改了哪些文件、下一步建议。
```

---

# 下一步计划

下一步建议用户先本地一次性测试框架闭环。

测试通过后，再开始精修 01 小说解析系统：

1. 明确小说文本输入文件位置
2. 明确章节 / 段落 / 事件 / 候选角色 / 候选场景 / 候选道具的输出结构
3. 只提出资产候选，不直接写入长篇共享资产库
4. 输出真实 `novel_analysis.json`
5. 把关键产物登记到 `manifest.json` 和 `artifacts.db`
6. 跑完释放本地资源

---

# 用户最新补充要求

用户要求：

```text
先把所有子系统的框架都弄起来，再一次性测试，慢慢精细打磨每一步。
每一步改动都写入 README 或文档。
后续尽量连续修改，不需要每一次小改动都让用户点击确认。
```

该要求为后续开发协作最高规则之一。
