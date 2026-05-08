# AI Short Drama Agent Canvas System

这是一个本地 AI 短剧 / 漫剧生产工作台。

项目已经从旧的模块流水线结构，改造成：

```text
Canvas 状态机
+ Agent 调度
+ Executor 执行
+ 文件任务队列
+ 前端可视化工作台
+ ComfyUI / LTX / CosyVoice2 接入骨架
```

旧结构不再作为默认入口。旧模块如果还需要参考，后续应移动到 `legacy/`。

---

## 当前核心架构

```text
run.py
backend/
  app/          # 项目、Canvas、Node、Task、HTTP API
  agents/       # Director / Writer / Asset / Storyboard / Reviewer / Repair
  executors/    # Image / Grid / Audio / Video / Final
  workers/      # 文件任务队列 runner
  schemas/      # Canvas / Node / Task schema
frontend/       # Vite + React 工作台
projects/       # 本地项目数据、节点、任务、素材、成片
```

核心原则：

```text
Canvas 负责状态
Node 负责内容
Agent 负责判断
Executor 负责执行
Task 负责排队
UI 负责可视化和人工干预
```

---

## 本地运行

### 1. 初始化 Demo 项目

```bash
python run.py init --project demo_project
```

### 2. 单步推进

```bash
python run.py step --project demo_project
```

### 3. 自动运行直到空闲

```bash
python run.py run --project demo_project
```

### 4. 启动后端 API

```bash
python run.py serve --host 127.0.0.1 --port 7860
```

后端 API 默认地址：

```text
http://127.0.0.1:7860
```

---

## 前端工作台

```bash
cd frontend
npm install
npm run dev
```

前端默认读取：

```text
http://127.0.0.1:7860/api/projects/demo_project
```

页面包含：

```text
项目阶段
Storyboard Canvas
Grid View
Asset Hub
Task Center
Node Detail
```

---

## API

```text
GET    /api/projects
GET    /api/projects/{project_id}
GET    /api/projects/{project_id}/canvas
GET    /api/projects/{project_id}/nodes
GET    /api/projects/{project_id}/nodes/{node_id}
GET    /api/projects/{project_id}/tasks
POST   /api/projects/{project_id}/init
POST   /api/projects/{project_id}/step
POST   /api/projects/{project_id}/run
POST   /api/projects/{project_id}/refresh
PATCH  /api/projects/{project_id}
PATCH  /api/projects/{project_id}/nodes/{node_id}
```

---

## Agent 分工

```text
director_agent      总调度，判断下一步，排任务，运行队列
writer_agent        小说解析、剧本块生成骨架
asset_agent         角色、场景、道具资产生成骨架
storyboard_agent    shot 与 grid 生成骨架
reviewer_agent      节点质量检查骨架
repair_agent        局部返工骨架
```

---

## Executor 分工

```text
image_executor      分镜图执行器，后续接 ComfyUI 生图工作流
grid_executor       宫格拼图执行器，后续接真实拼图逻辑
audio_executor      配音与字幕执行器，后续接 CosyVoice2
video_executor      视频执行器，后续接 ComfyUI / LTX2.3
final_assembler     成片合成执行器，后续接 FFmpeg
```

---

## 数据结构

每个项目生成在：

```text
projects/{project_id}/
  project.json
  canvas.json
  nodes/*.json
  tasks/pending/*.json
  tasks/running/*.json
  tasks/done/*.json
  tasks/failed/*.json
  assets/
  images/
  grids/
  audio/
  videos/
  final/
```

`canvas.json` 只保存轻量索引，具体内容放在 `nodes/*.json`。

---

## 重要说明

这次改造不是继续维护旧的：

```text
00_style_system → 01_novel_parser → 02_script_writer → ... → 10_final_assembly
```

而是把项目默认方向切到：

```text
Agent Canvas 短剧生产工作台
```

旧模块后续只作为参考资产，不再作为默认总控入口。

详细总方案见：

```text
docs/AGENT_CANVAS_UI_REFACTOR_PLAN.md
```
