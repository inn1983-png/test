# AI Short Drama Agent Canvas System

这是一个本地 AI 短剧 / 漫剧生产工作台。当前仓库只保留新系统，不再保留旧的 `00-10` 模块流水线。

## 核心架构

```text
run.py
backend/      Agent Canvas 后端、Agent、Executor、任务队列、配置和工作流管理
frontend/     React + Vite 可视化工作台
docs/         改造计划、完成清单、开发日志
projects/     本地运行时自动生成，不提交媒体产物
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

## 本地运行

```bash
pip install -r requirements.txt
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

## UI 页面

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

## ComfyUI 工作流 JSON 在线上传

前端 `Settings` 页面支持上传 ComfyUI workflow JSON，按功能分类保存：

```text
projects/{project_id}/workflows/image/
projects/{project_id}/workflows/video/
projects/{project_id}/workflows/audio/
projects/{project_id}/workflows/grid/
projects/{project_id}/workflows/final/
projects/{project_id}/workflows/utility/
```

## 文档

```text
docs/AGENT_CANVAS_UI_REFACTOR_PLAN.md
docs/AGENT_CANVAS_COMPLETION_CHECKLIST.md
docs/DEVELOPMENT_LOG.md
```
