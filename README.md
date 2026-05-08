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
python run.py serve --host 127.0.0.1 --port 7860
```

前端：

```bash
cd frontend
npm install
npm run dev
```

测试：

```bash
pytest
```

前端默认读取：

```text
http://127.0.0.1:7860/api/projects/demo_project
```

Windows 一键启动：

```text
一键启动.bat    启动后端和前端，不启动 Gemma
TTS启动.bat     单独启动 IndexTTS WebUI，默认端口 7861
```

## UI 页面

```text
Dashboard     项目总览 + 导入原文 + 一键运行 + 分阶段运行
Script        小说 / 剧本节点 + 原文导入
Assets        角色 / 场景 / 道具资产 tab + 角色音色选择 + 资产轻量编辑 + 锁定全部资产
Storyboard    shot 卡片 + 搜索 / 状态过滤 / 批量审核修复重跑 + grid 宫格视图
Tasks         任务中心，支持重试 / 取消 / 查看日志
Preview       final_manifest 查看 + 成片路径 / 可用时视频预览
Settings      本地路径配置 + ComfyUI 工作流 JSON 上传 + workflow mapping + 本地检测
Node Detail   右侧节点详情，支持编辑 / 重跑 / 审核 / 修复 / 锁定
```

## 本机路径配置

当前音频方案是 IndexTTS。ComfyUI、IndexTTS、FFmpeg 都是本地配置项，以下内容不写死，由你在 `Settings` 页面或 `projects/{project_id}/settings.json` 中设置：

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "image_workflow": "workflows/image/storyboard_image.json",
  "video_workflow": "workflows/video/ltx23_grid_video.json",
  "indextts_root": "index-tts",
  "indextts_voice_index": "examples/voice_index.json",
  "indextts_command": "",
  "narrator_voice_id": "voice_06",
  "default_voice_id": "voice_06",
  "ffmpeg_path": "ffmpeg",
  "llm_provider": "llama_cpp",
  "llm_base_url": "http://127.0.0.1:8080/v1",
  "llm_model": "gemma-4-31B-it-Q4_K_M"
}
```

IndexTTS 命令支持占位符：

```text
{text}
{text_file}
{output_file}
{voice_id}
{voice_file}
{project_dir}
{indextts_root}
```

保存位置：

```text
projects/{project_id}/settings.json
```

也可以在前端 `Settings` 页面直接修改。

如果本机 `index-tts/` 位于仓库根目录，可以在 Settings 中按你的本地 Python / venv / shell 方式配置 `indextts_command`。仓库不会自动写死 IndexTTS 推理脚本路径、模型路径或音色参数。

旁白音色使用 `narrator_voice_id`，当前 demo 配置固定为 `voice_06`。角色音色在 Assets 页的 Characters tab 中为每个角色资产单独选择并保存为 `voice_id`。

## 本地 LLM

Settings 支持配置本地 `llama.cpp` / Gemma OpenAI-compatible API：

```text
llm_provider
llm_base_url
llm_model
llama_cpp_root
llama_cpp_server_exe
llama_cpp_model_path
llama_cpp_mmproj_path
llama_cpp_context_size
llama_cpp_gpu_layers
llama_cpp_port
```

本地 Gemma 只会受到后端实际发送给 `llama.cpp` 的 prompt / messages 影响；当前 Codex 对话不会自动进入它的上下文。

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

ComfyUI workflow node id 和 input name 在 Settings 页面配置：

```text
image.prompt_node / image.prompt_input
image.negative_node / image.negative_input
video.prompt_node / video.prompt_input
video.image_node / video.image_input
```

## 已完成的仓库内生产钩子

```text
原文导入 API + UI
Dashboard 分阶段 action API + UI
Writer / Asset / Storyboard / Reviewer / Repair Agent
Storyboard 搜索、状态过滤、批量审核 / 修复 / 重跑
Assets 角色 / 场景 / 道具 tab、角色音色选择、资产表单编辑、锁定全部资产
ComfyUI workflow 上传与 mapping
ComfyUI ping、FFmpeg check、IndexTTS command check、workflow JSON validation
IndexTTS 音色库读取和默认音色选择
本地 llama.cpp / Gemma LLM 配置和 LLM check
真实 grid_4 / grid_6 / grid_9 宫格拼图
ComfyUI history 输出路径解析
IndexTTS 本地命令适配器
FFmpeg final.mp4 合成器
Preview final_manifest 查看
Task 日志、traceback、耗时记录
Tasks UI 日志查看
pytest 基础测试
```

## UI 中可以完成

```text
导入小说正文
一键运行
分阶段运行
上传 workflow JSON
配置 workflow mapping
配置 IndexTTS command
查看任务日志
查看 final manifest
```

## 文档

```text
docs/AGENT_CANVAS_UI_REFACTOR_PLAN.md
docs/AGENT_CANVAS_COMPLETION_CHECKLIST.md
docs/DEVELOPMENT_LOG.md
docs/CODEX_REMAINING_WORK_PLAN.md
```
