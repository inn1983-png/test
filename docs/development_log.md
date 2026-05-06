# 开发记录与协作规则

本文档记录每一轮框架改动，方便用户、新对话、本地 Codex 接手。

---

# 协作规则

1. 每一轮改动前，先说明准备做什么。
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

---

# 当前开发阶段

当前阶段：打磨 00 总控基座。

目标：先把运行目录、短篇/长篇模式、共享资产库、产物索引、模块调度、显存释放规则全部定稳，再进入 01 小说解析系统。

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

---

# 下一步计划

下一步继续打磨 00 总控基座：

1. 增加 pipeline 配置校验
2. 增加本地模型释放命令配置
3. 增加空流程自检命令
4. 确保 00 可以跑通空流程
5. 进入 01 小说解析系统前，让 00 的输入/输出/清理/查询全部稳定

---

# 用户最新补充要求

用户要求：

```text
每一步改动都写入 README 或文档。
每一步准备做什么都先告诉用户，方便用户补充要求。
```

该要求为后续开发协作最高规则之一。
