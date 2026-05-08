# AI Short Drama Agent Canvas System

这是一个本地 AI 短剧 / 漫剧生产工作台。

项目已经从旧的模块流水线结构，改造成：

```text
Canvas 状态机
+ Agent 调度
+ Executor 执行
+ 文件任务队列
+ 前端可视化工作台
+ ComfyUI / LTX / CosyVoice2 / FFmpeg 可配置接入
```

旧结构不再作为默认入口。旧模块如果还需要参考，后续应移动到 `legacy/`。

---

## 当前核心架构

```text
run.py
backend/
  app/          # 项目、Canvas、Node、Task、Settings、Workflow、HTTP API
  agents/       # Director / Writer / Asset / Storyboard / Reviewer / Repair
  executors/    # Image / Grid / Audio / Video / Final
  workers/      # 文件任务队列 runner
  schemas/      # Canvas / Node / Task schema
frontend/       # Vite + React 工作台
projects/       # 本地项目数据、节点、任务、素材、成片、工作流
```

核心原则：

```text
Canvas 负责状态
Node 负责内容
Agent 负责判断
Executor 负责执行
Task 负责排队
Workflow 负责 ComfyUI JSON 分类管理
Settings 负责本机路径配置
UI 负责可视化和人工干预
```

---

## 本地运行

```bash
python run.py init --project demo_project
python run.py run --project demo_project
python run.py serve --host 127.0.0.1 --port 7860
```

前端：

```bash
cd frontend
npm install
npm run dev
```

前端默认读取：

```text
http://127.0.0.1:7860/api/projects/demo_project
```

---

## UI 页面

当前前端工作台包含：

```text
Dashboard     项目总览
Script        小说 / 剧本节点
Assets        角色 / 场景 / 道具资产
Storyboard    shot 卡片 + grid 宫格视图
Tasks         任务中心，支持重试 / 取消
Preview       成片预览入口
Settings      本地路径配置 + ComfyUI 工作流 JSON 上传
Node Detail   右侧节点详情，支持编辑 / 重跑 / 审核 / 修复 / 锁定
```

---

## 本机路径配置

以下内容不写死，由你本地设置：

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "image_workflow": "workflows/image/storyboard_image.json",
  "video_workflow": "workflows/video/ltx23_grid_video.json",
  "cosyvoice2_command": "",
  "ffmpeg_path": "ffmpeg"
}
```

保存位置：

```text
projects/{project_id}/settings.json
```

也可以在前端 `Settings` 页面直接修改。

---

## ComfyUI 工作流 JSON 在线上传

前端 `Settings` 页面支持上传 ComfyUI workflow JSON。

按功能分类保存：

```text
projects/{project_id}/workflows/image/
projects/{project_id}/workflows/video/
projects/{project_id}/workflows/audio/
projects/{project_id}/workflows/grid/
projects/{project_id}/workflows/final/
projects/{project_id}/workflows/utility/
```

分类建议：

```text
image   分镜图、角色图、场景图、道具图
video   LTX2.3、图生视频、宫格图生视频
audio   CosyVoice2、配音、字幕
grid    grid_4 / grid_6 / grid_9 拼宫格
final   成片合成
utility 反推提示词、元数据提取、辅助工作流
```

上传 API：

```text
POST /api/projects/{project_id}/workflows
```

Body：

```json
{
  "category": "video",
  "name": "ltx23_grid_video.json",
  "content": "{...ComfyUI workflow JSON...}"
}
```

`content` 支持：

```text
1. 原始 JSON 字符串
2. JSON object
3. base64 JSON
```

---

## API

```text
GET    /api/projects
GET    /api/projects/{project_id}
GET    /api/projects/{project_id}/canvas
GET    /api/projects/{project_id}/settings
GET    /api/projects/{project_id}/workflows
GET    /api/projects/{project_id}/nodes
GET    /api/projects/{project_id}/nodes/{node_id}
GET    /api/projects/{project_id}/tasks
POST   /api/projects/{project_id}/init
POST   /api/projects/{project_id}/step
POST   /api/projects/{project_id}/run
POST   /api/projects/{project_id}/refresh
POST   /api/projects/{project_id}/workflows
POST   /api/projects/{project_id}/nodes/{node_id}/rerun
POST   /api/projects/{project_id}/nodes/{node_id}/review
POST   /api/projects/{project_id}/nodes/{node_id}/repair
POST   /api/projects/{project_id}/nodes/{node_id}/lock
POST   /api/projects/{project_id}/tasks/{task_id}/retry
POST   /api/projects/{project_id}/tasks/{task_id}/cancel
POST   /api/projects/{project_id}/tasks/{task_id}/log
PATCH  /api/projects/{project_id}
PATCH  /api/projects/{project_id}/settings
PATCH  /api/projects/{project_id}/nodes/{node_id}
```

---

## 数据结构

每个项目生成在：

```text
projects/{project_id}/
  project.json
  settings.json
  canvas.json
  nodes/*.json
  tasks/pending/*.json
  tasks/running/*.json
  tasks/done/*.json
  tasks/failed/*.json
  tasks/cancelled/*.json
  tasks/logs/*.log
  workflows/image/*.json
  workflows/video/*.json
  workflows/audio/*.json
  workflows/grid/*.json
  workflows/final/*.json
  workflows/utility/*.json
  assets/
  images/
  grids/
  audio/
  videos/
  final/
```

`canvas.json` 只保存轻量索引，具体内容放在 `nodes/*.json`。

---

## 开发日志

详细改造记录和本地配置说明见：

```text
docs/DEVELOPMENT_LOG.md
docs/AGENT_CANVAS_UI_REFACTOR_PLAN.md
```
