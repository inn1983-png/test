# 00 总控系统

## 模块定位

00 总控系统是整个项目的运行基座。

它不负责解析小说，不负责写剧本，不负责生图，不负责生视频。

它只负责：

1. 创建运行上下文
2. 创建短篇项目目录或长篇章节目录
3. 初始化长篇共享资产库
4. 初始化产物数据库 `artifacts.db`
5. 初始化轻量摘要 `manifest.json`
6. 初始化运行状态表 `run_status.json`
7. 按 `pipeline.json` 顺序调用各个子系统
8. 把运行上下文传给每个模块
9. 让每个模块知道自己的正式输出目录
10. 提供安全清理工具
11. 提供产物查询工具
12. 提供 pipeline 配置校验工具
13. 提供模块输入依赖检查
14. 提供局部运行：`--from-module` / `--only-module`
15. 提供 dry-run 预演模式
16. 提供空流程自检工具
17. 提供完整框架流程自检工具
18. 提供本地模型释放命令配置

---

# 为什么必须先打磨 00

如果没有稳定的 00，后面的 01–10 会反复返工。

常见问题包括：

```text
每个模块各写各的 output
后一步不知道前一步输出在哪里
长篇角色/场景/道具没地方复用
单章数据和全书资产混在一起
用户不知道哪些文件可以删除
Codex 不知道该从哪里接手
不知道哪个模块失败、失败前哪些模块成功
只想重跑一个模块却被迫从头跑
模块缺上游文件还继续盲跑
```

所以工程顺序是：

```text
先搭 00 运行基座
再搭 01–10 子系统框架
再逐步精修每个子系统
```

---

# 当前框架闭环状态

当前 01–10 已全部具备框架级关键产物输出。

完整跑一次 project 模式后，会生成：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
03_character_library/characters.json
04_scene_library/scenes.json
05_prop_library/props.json
06_storyboard/storyboard.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
09_video/video_manifest.json
10_final_assembly/final.mp4
```

这些关键产物会登记到：

```text
manifest.json 的 key_outputs
artifacts.db
```

说明：

```text
当前生成的是 scaffold 占位产物，不是真实 AI 结果。
目的是先打通 00→10 的完整流程、依赖检查、manifest 登记、状态记录。
后续再逐步精修每个模块的真实业务逻辑。
```

---

# 运行模式

## 1. 短篇 / 单章项目模式

适合：

- 一次性短篇故事
- 单章测试
- 单模块调试
- 不需要长期共享角色/场景/道具的项目

运行命令：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001
```

输出目录：

```text
workspace/projects/project_test_001/
```

## 2. 长篇小说章节模式

适合：

- 长篇小说
- 连续剧集
- 多章节共用角色、场景、道具、音色

运行命令：

```bash
python 00_main_controller/run_pipeline.py --mode book_chapter --book-id book_001 --chapter-id chapter_001
```

章节运行目录：

```text
workspace/books/book_001/chapters/chapter_001/
```

全书共享资产库：

```text
workspace/books/book_001/shared_assets/
```

全书记忆目录：

```text
workspace/books/book_001/global_memory/
```

---

# 00 核心文件

```text
00_main_controller/run_pipeline.py       # 总控入口
00_main_controller/validate_pipeline.py  # pipeline 配置校验
00_main_controller/self_check.py         # 00 空流程 + 01–10 框架闭环自检
00_main_controller/cleanup_workspace.py  # 安全清理工具
00_main_controller/query_artifacts.py    # 产物查询工具
00_common/workspace_manager.py           # 项目目录 / 长篇目录管理
00_common/module_runner.py               # 子系统调用器
00_common/module_contracts.py            # 模块输入 / 输出契约检查
00_common/run_status.py                  # 模块运行状态记录
00_common/base_module.py                 # 子系统基础工具
00_common/artifact_db.py                 # SQLite 产物数据库
00_common/artifact_registry.py           # 产物登记器
00_common/artifact_resolver.py           # 后续模块查找上一步资产
00_common/resource_manager.py            # 本地模型显存释放 / 外部释放命令配置
configs/module_contracts.json            # 模块依赖契约配置
configs/local_resource_release.json      # 本地资源释放命令配置
```

---

# pipeline 校验

单独校验：

```bash
python 00_main_controller/validate_pipeline.py --pipeline pipeline.json
```

严格顺序校验：

```bash
python 00_main_controller/validate_pipeline.py --pipeline pipeline.json --strict-order
```

`run_pipeline.py` 默认会在运行前先执行校验。

如果确实要跳过校验：

```bash
python 00_main_controller/run_pipeline.py --skip-validation
```

---

# 局部运行

## 从指定模块开始跑

例如 01–05 已经完成，只想从 06 分镜开始继续：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 06_storyboard
```

## 只跑一个模块

例如只重跑 06 分镜：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 06_storyboard
```

`--from-module` 和 `--only-module` 不能同时使用。

---

# dry-run 预演模式

只打印本次运行计划，不真正执行模块：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --dry-run
```

只预演单个模块：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser --dry-run
```

它会打印：

```text
mode
run_id
run_dir
input_dir
shared_assets_dir
global_memory_dir
每个模块的 input_dir
每个模块的 output_dir
每个模块 requires
每个模块 produces
```

---

# 模块依赖检查

依赖配置文件：

```text
configs/module_contracts.json
```

运行模块前，00 会按以下顺序查找上游产物：

```text
1. manifest.json 的 key_outputs
2. artifacts.db
3. workspace 中约定的模块输出路径
```

如果缺少上游产物，00 会在模块运行前阻断，而不是盲目继续。

跳过依赖检查：

```bash
python 00_main_controller/run_pipeline.py --skip-dependency-check
```

---

# 运行状态记录

每次运行会生成：

```text
run_status.json
```

它记录：

```text
pipeline
每个模块 status
每个模块 start_time
每个模块 end_time
每个模块 duration_seconds
每个模块 return_code
每个模块 message
```

常见状态：

```text
pending   等待运行
running   正在运行
success   运行成功
failed    运行失败
blocked   依赖缺失，被 00 阻断
skipped   跳过
```

---

# 自检命令

## 只初始化短篇运行目录，不运行任何模块

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id self_check_project --empty-pipeline
```

## 只初始化长篇章节目录，不运行任何模块

```bash
python 00_main_controller/run_pipeline.py --mode book_chapter --book-id self_check_book --chapter-id chapter_001 --empty-pipeline
```

## 一键自检 00 + 01–10 框架闭环

```bash
python 00_main_controller/self_check.py
```

它会自动检查：

```text
pipeline.json 是否能通过严格顺序校验
短篇 project 空流程是否能初始化
长篇 book_chapter 空流程是否能初始化
runtime_context.json 是否存在
manifest.json 是否存在
artifacts.db 是否存在
run_status.json 是否存在
shared_assets 默认文件是否存在
global_memory 默认文件是否存在
--only-module + --dry-run 是否可用
project 模式完整 01–10 框架流程是否能跑通
01–10 关键产物是否全部生成
01–10 关键产物是否登记到 manifest.key_outputs
run_status.json 中 01–10 是否全部 success
```

默认自检结束后会删除临时目录。

如果要保留自检目录：

```bash
python 00_main_controller/self_check.py --keep
```

---

# 本地模型释放配置

每个模块仍然必须在 `finally` 中调用：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

默认行为：

```text
1. gc.collect()
2. torch.cuda.empty_cache()
3. torch.cuda.ipc_collect()
```

外部释放命令通过下面文件配置：

```text
configs/local_resource_release.json
```

默认关闭，避免误停 ComfyUI、本地 LLM、TTS 服务或其他用户正在使用的进程。

---

# 运行上下文

每次正式运行都会生成：

```text
runtime_context.json
```

每个模块运行时都会收到环境变量：

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

# 产物索引规则

正式规则：

```text
manifest.json = 轻量摘要 + 关键输出索引
artifacts.db = 所有产物详细记录
真实目录 = 保存实际文件
```

关键输出要进入：

```text
manifest.json 的 key_outputs
artifacts.db
```

批量产物只进入：

```text
artifacts.db
```

不要全部塞进 `manifest.json`。

---

# 后续模块查找上一步资产

统一使用：

```text
00_common/artifact_resolver.py
```

查找顺序：

```text
1. manifest.json 的 key_outputs
2. artifacts.db
3. 约定目录兜底
```

---

# 清理工具

清理短篇项目：

```bash
python 00_main_controller/cleanup_workspace.py project --project-id project_test_001 --yes
```

清理长篇某一章，保留共享资产库：

```bash
python 00_main_controller/cleanup_workspace.py chapter --book-id book_001 --chapter-id chapter_001 --yes
```

清理整本长篇项目，包括共享资产库：

```bash
python 00_main_controller/cleanup_workspace.py book --book-id book_001 --yes
```

安全规则：

```text
cleanup_workspace.py 只允许删除 workspace/ 下的目录
没有 --yes 不会真正删除
```

---

# 产物查询工具

查看某次运行的关键输出：

```bash
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001 --keys
```

查看某次运行的所有产物：

```bash
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001
```

按模块过滤：

```bash
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001 --module 01_novel_parser
```

按类型过滤：

```bash
python 00_main_controller/query_artifacts.py --run-dir workspace/projects/project_test_001 --type image
```

---

# 运行数据规则

正式运行时，模块不要长期写自己的 `output/`。

正式输出应该写入：

```text
workspace/projects/{project_id}/{module_name}/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/{module_name}/
```

模块自己的 `input/` 和 `output/` 只用于单模块调试。

---

# 00 不做的事

00 不负责：

- 小说解析
- 剧本改编
- 角色合并
- 场景生成
- 道具生成
- 分镜生成
- 生图
- 配音
- 生视频
- 成片拼接

这些必须交给对应模块。

---

# 当前后续建议

1. 在真实本地环境执行 `python 00_main_controller/self_check.py`
2. 如果通过，就说明 00 + 01–10 框架闭环成功
3. 接下来开始逐步精修 01 小说解析系统
