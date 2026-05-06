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

当前阶段：00 总控基座基本打磨完成，准备进入 01 小说解析系统。

00 当前已经覆盖：

```text
短篇 / 长篇运行目录
长篇 shared_assets / global_memory 初始化
runtime_context.json
manifest.json
artifacts.db
pipeline 校验
模块调度
显存 / 本地资源释放入口
安全清理
产物查询
空流程自检
```

进入 01 前，建议用户在本地执行：

```bash
python 00_main_controller/self_check.py
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

自检命令：

```bash
python 00_main_controller/self_check.py
```

空流程命令：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id self_check_project --empty-pipeline
python 00_main_controller/run_pipeline.py --mode book_chapter --book-id self_check_book --chapter-id chapter_001 --empty-pipeline
```

资源释放配置文件：

```text
configs/local_resource_release.json
```

---

# 下一步计划

下一步建议进入 01 小说解析系统。

01 的第一轮目标不是复杂 AI 改写，而是先把输入输出边界打稳：

1. 明确小说文本输入文件位置
2. 明确章节 / 段落 / 事件 / 候选角色 / 候选场景 / 候选道具的输出结构
3. 只提出资产候选，不直接写入长篇共享资产库
4. 输出关键产物 `novel_analysis.json`
5. 把关键产物登记到 `manifest.json` 和 `artifacts.db`
6. 跑完释放本地资源

---

# 用户最新补充要求

用户要求：

```text
每一步改动都写入 README 或文档。
每一步准备做什么都先告诉用户，方便用户补充要求。
```

该要求为后续开发协作最高规则之一。
