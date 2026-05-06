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
6. 按 `pipeline.json` 顺序调用各个子系统
7. 把运行上下文传给每个模块
8. 让每个模块知道自己的正式输出目录
9. 提供安全清理工具
10. 提供产物查询工具

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
```

所以工程顺序是：

```text
先搭 00 运行基座
再搭 01 小说解析系统
再逐步打磨 02–10
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

---

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
00_main_controller/cleanup_workspace.py  # 安全清理工具
00_main_controller/query_artifacts.py    # 产物查询工具
00_common/workspace_manager.py           # 项目目录 / 长篇目录管理
00_common/module_runner.py               # 子系统调用器
00_common/base_module.py                 # 子系统基础工具
00_common/artifact_db.py                 # SQLite 产物数据库
00_common/artifact_registry.py           # 产物登记器
00_common/artifact_resolver.py           # 后续模块查找上一步资产
00_common/resource_manager.py            # 本地模型显存释放
```

---

# 运行上下文

每次正式运行都会生成：

```text
runtime_context.json
```

它记录：

```text
mode
run_id
project_id
book_id
chapter_id
run_dir
input_dir
shared_assets_dir
global_memory_dir
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

本项目不使用巨大 `manifest.json` 存所有文件。

正式规则：

```text
manifest.json = 轻量摘要 + 关键输出索引
artifacts.db = 所有产物详细记录
真实目录 = 保存实际文件
```

## 关键输出

例如：

```text
novel_analysis.json
script.json
characters.json
storyboard.json
image_manifest.json
final_audio.wav
video_manifest.json
final.mp4
```

关键输出要进入：

```text
manifest.json 的 key_outputs
artifacts.db
```

## 批量产物

例如：

```text
shot_001.png
shot_002.png
clip_001.mp4
clip_002.mp4
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

这样后续模块不用猜文件在哪里。

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

# 当前 00 后续待做

1. 增加 pipeline 配置校验
2. 增加本地模型释放命令配置
3. 增加空流程自检命令
4. 进入 01 小说解析系统前，先确保 00 可以跑通空流程
