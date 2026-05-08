# Agent Canvas UI Refactor Plan

目标：把项目改为本地 AI 短剧 / 漫剧生产工作台。

核心结构：

```text
Canvas 状态机 + Agent 调度 + Executor 执行 + Task 队列 + UI 工作台
```

保留的新系统目录：

```text
backend/
frontend/
docs/
run.py
requirements.txt
```

旧的 `00-10` 模块流水线、旧 `web_ui`、旧 `configs`、旧 `pipeline.json` 不再保留在仓库。
