# Codex Remaining Work Plan

本计划用于让 Codex 继续完成 Agent Canvas 新系统。仓库当前只保留新系统，不再保留旧 `00-10` 模块流水线。

## 0. 当前仓库状态

当前已完成：

```text
backend/
frontend/
docs/
run.py
requirements.txt
README.md
```

已完成的基础能力：

```text
Canvas 状态机
Node 文件存储
Task 文件队列
Settings 本地配置
Workflow 分类上传
Director / Writer / Asset / Storyboard / Reviewer / Repair Agents
Image / Grid / Audio / Video / Final Executors
React 工作台 UI
```

但是目前还有若干生产闭环没有完成。以下任务按优先级执行。

---

# Phase 1: Source Input and Project Creation

## 1.1 Backend: add source text import API

新增 API：

```text
POST /api/projects/{project_id}/source
```

Body：

```json
{
  "title": "chapter title",
  "content": "novel text"
}
```

要求：

1. 保存 `source_001` node。
2. 清空旧的 script / asset / shot / grid / media task 节点，避免重复运行污染。
3. 更新 project title/current_stage/progress。
4. 刷新 canvas。

建议新增文件：

```text
backend/app/project_actions.py
```

函数：

```python
import_source_text(project_id, title, content)
reset_project_generated_nodes(project_id)
```

## 1.2 Frontend: add source import panel

在 UI 的 `Script` 页面或新增 `Source` 页面：

1. 输入项目标题。
2. 粘贴小说正文。
3. 点击“导入原文”。
4. 导入后自动刷新数据。

验收：

```text
前端能导入一段小说文本，后端生成 source_001，Run All 后生成 script/assets/storyboard。
```

---

# Phase 2: Workflow Node Mapping System

当前 image/video executor 写死了：

```text
PROMPT_NODE
NEGATIVE_NODE
IMAGE_NODE
```

这必须改成 UI 可配置。

## 2.1 Backend: add workflow mapping settings

在 `settings.json` 中新增：

```json
{
  "workflow_mappings": {
    "image": {
      "prompt_node": "",
      "prompt_input": "text",
      "negative_node": "",
      "negative_input": "text"
    },
    "video": {
      "prompt_node": "",
      "prompt_input": "text",
      "image_node": "",
      "image_input": "image"
    }
  }
}
```

## 2.2 Executor: use mapping instead of placeholders

修改：

```text
backend/executors/image_executor.py
backend/executors/video_executor.py
```

要求：

1. 从 settings 读取 mapping。
2. 没配置时返回 `needs_review`，不要直接失败。
3. 错误信息写清楚缺哪个 node id。

## 2.3 Frontend: mapping editor

在 Settings 页面新增：

```text
Image Workflow Mapping
Video Workflow Mapping
```

字段：

```text
prompt_node
prompt_input
negative_node
negative_input
image_node
image_input
```

验收：

```text
用户上传 ComfyUI workflow JSON 后，可以在 UI 填 node id 和 input name。
Executor 使用用户配置 patch workflow。
```

---

# Phase 3: Real Grid Builder

当前 `backend/executors/grid_executor.py` 只是占位。

## 3.1 Add Pillow dependency

`requirements.txt` 增加：

```text
pillow>=10.0.0
```

## 3.2 Implement real grid image builder

修改：

```text
backend/executors/grid_executor.py
```

要求：

1. 根据 grid node 的 `shot_ids` 读取每个 shot 的 `image_path`。
2. 从 `projects/{project_id}/images/` 找真实图片。
3. 支持：

```text
grid_4 = 2x2
grid_6 = 3x2 或 2x3
grid_9 = 3x3
```

4. 缺图时 node 标记 `needs_review`，不要生成假图。
5. 生成真实文件：

```text
projects/{project_id}/grids/{grid_id}.png
```

6. 更新 grid node：

```json
{
  "status": "done",
  "grid_path": "grids/grid_001.png",
  "shot_count": 4
}
```

验收：

```text
只要 shot image_path 对应真实图片存在，grid_executor 能生成真实宫格图。
```

---

# Phase 4: ComfyUI Result Path Extraction

当前 image/video executor 调用 ComfyUI 后，没有从 history 里解析真实输出文件。

## 4.1 Backend: add output extractor

修改：

```text
backend/executors/comfyui_client.py
```

新增函数：

```python
extract_images_from_history(history) -> list[str]
extract_videos_from_history(history) -> list[str]
```

要求：

1. 兼容 ComfyUI history 里的 `outputs`。
2. 读取 `images` / `gifs` / `videos` / `filename` 字段。
3. 返回相对路径或文件名。

## 4.2 Image executor saves real output path

修改：

```text
backend/executors/image_executor.py
```

要求：

1. 成功后从 history 解析第一张图。
2. 如果 ComfyUI 返回的是外部文件名，记录：

```json
{
  "comfyui_output": "xxx.png",
  "image_path": "images/shot_001.png" 或真实路径
}
```

3. 如果未解析到图片，标记 `needs_review`。

## 4.3 Video executor saves real output path

修改：

```text
backend/executors/video_executor.py
```

要求同上，解析视频输出。

验收：

```text
ComfyUI 生成完成后，shot/video node 中能看到真实输出文件名或路径。
```

---

# Phase 5: CosyVoice2 Executor

当前 audio executor 只预留 `cosyvoice2_command`。

## 5.1 Settings

Settings 保留：

```json
{
  "cosyvoice2_command": "python D:/CosyVoice2/infer.py --text {text_file} --output {output_file} --voice {voice_id}",
  "default_voice_id": "default"
}
```

## 5.2 Audio executor implementation

修改：

```text
backend/executors/audio_executor.py
```

要求：

1. 为 node 文本生成临时 txt：

```text
projects/{project_id}/audio/{node_id}.txt
```

2. 使用 `subprocess.run` 调用配置命令。
3. 支持占位符：

```text
{text}
{text_file}
{output_file}
{voice_id}
{project_dir}
```

4. 如果 command 为空，标记 `needs_review`。
5. 如果执行失败，标记 `failed` 并写入 error。
6. 如果 wav 文件存在，标记 `done`。

验收：

```text
配置 CosyVoice2 命令后，audio_executor 生成真实 wav。
```

---

# Phase 6: FFmpeg Final Assembly

当前 final assembler 只写 manifest，不真正拼接。

## 6.1 Add final task enqueue

Director 需要在所有 video done 后，自动 enqueue：

```text
final_assembly -> final_assembler
```

## 6.2 Implement FFmpeg assembly

修改：

```text
backend/executors/assembly_manifest.py
backend/executors/final_assembler.py
```

要求：

1. 收集所有 video_path。
2. 生成 concat list：

```text
projects/{project_id}/final/concat.txt
```

3. 使用 settings.ffmpeg_path 调用：

```bash
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy final.mp4
```

4. 如果 copy 失败，降级转码：

```bash
ffmpeg -y -f concat -safe 0 -i concat.txt -c:v libx264 -c:a aac final.mp4
```

5. 如果没有真实视频，标记 `needs_review`。

验收：

```text
多个 video clip 存在时，能生成 projects/{project_id}/final/final.mp4。
```

---

# Phase 7: Task Logs and Error Visibility

当前 task log 只有辅助函数，UI 没有完整查看日志。

## 7.1 Task runner logging

修改：

```text
backend/workers/task_runner.py
```

要求：

1. 任务开始写 log。
2. 任务成功写 result。
3. 任务失败写 traceback。
4. task json 保存 started_at / finished_at / duration_seconds。

## 7.2 UI task log drawer

在 Tasks 页面：

1. 点击任务显示 log。
2. 显示 result/error。
3. 支持 retry/cancel。

验收：

```text
任何 executor 失败，UI 可直接看到失败原因。
```

---

# Phase 8: Better UI Production Flow

当前 UI 是基础多页面，需要补生产操作流。

## 8.1 Dashboard

增加：

```text
导入原文
一键生成剧本
一键生成资产
一键生成分镜
一键生成图片
一键生成视频
一键合成
```

每个按钮调用对应后端 action。

## 8.2 Storyboard

增加：

```text
shot 搜索
按状态过滤
批量审核
批量修复
批量重跑
显示 image_path 缩略图
显示 grid_path 缩略图
```

## 8.3 Assets

增加：

```text
角色 / 场景 / 道具 tab
编辑 visual_lock
编辑 negative_prompt
锁定资产
```

## 8.4 Settings

增加：

```text
ComfyUI ping 按钮
FFmpeg check 按钮
CosyVoice2 command check 按钮
Workflow JSON 格式校验
Workflow mapping 编辑器
```

验收：

```text
用户可以不改代码，只通过 UI 完成主要配置和重跑。
```

---

# Phase 9: Tests and Smoke Test

新增：

```text
tests/test_agent_pipeline.py
tests/test_project_actions.py
tests/test_workflow_store.py
tests/test_grid_executor.py
tests/test_settings_store.py
```

至少覆盖：

1. 导入 source。
2. Writer 生成 script。
3. Asset 生成角色/场景/道具。
4. Storyboard 生成 shot/grid。
5. Workflow JSON 上传和读取。
6. Grid executor 用 fixtures 生成真实 grid png。
7. Task runner 成功/失败状态转移。

验收：

```bash
pytest
```

能跑通不依赖 ComfyUI/CosyVoice2/FFmpeg 的单元测试。

---

# Phase 10: Local-only tasks

以下必须在用户本机完成，不要写死进仓库。

## 10.1 ComfyUI

用户本地完成：

```text
1. 启动 ComfyUI。
2. 在 Settings 填 comfyui_url。
3. 上传真实 image/video workflow JSON。
4. 填写 workflow node mapping。
5. 测试 image/video executor。
```

## 10.2 CosyVoice2

用户本地完成：

```text
1. 安装 CosyVoice2。
2. 确认模型路径。
3. 配置 cosyvoice2_command。
4. 测试 audio executor。
```

## 10.3 FFmpeg

用户本地完成：

```text
1. 安装 FFmpeg。
2. 配置 ffmpeg_path。
3. 用真实 video clips 测试 final assembler。
```

---

# Final Acceptance Criteria

Codex 完成后，至少达到：

```text
1. 用户通过 UI 导入小说正文。
2. 点击 Run All 后生成 script/assets/storyboard/grid task。
3. Settings 能上传 workflow JSON 并配置 node mapping。
4. Grid executor 能生成真实宫格 png。
5. ComfyUI executor 能解析真实输出路径。
6. CosyVoice2 command 配置后能生成 wav。
7. FFmpeg 配置后能合成 final.mp4。
8. Task 页面能查看错误日志。
9. pytest 基础测试通过。
```

如果本地 ComfyUI/CosyVoice2/FFmpeg 未配置，对应任务必须显示 `needs_review`，不能生成假媒体文件。
