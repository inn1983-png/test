# Codex Remaining Work Plan

本仓库当前只保留 Agent Canvas 新系统，不再保留旧 `00-10` 模块流水线。

## 已由仓库完成

```text
Source import API and UI
Workflow node mapping settings and UI
Image executor uses configurable workflow mapping
Video executor uses configurable workflow mapping
ComfyUI history output extraction
Real grid_4 / grid_6 / grid_9 image builder
IndexTTS command adapter
FFmpeg final assembly
Task runner logs, traceback and duration
Task log viewer in UI
Basic pytest tests
```

## 已完成的增强项

以下增强项已经在仓库内完成，不依赖真实本地生成环境：

```text
1. Dashboard 单阶段按钮：只生成剧本 / 只生成资产 / 只生成分镜 / 只生成图片 / 只生成宫格 / 只生成音频 / 只生成视频 / 只合成。
2. Storyboard 搜索、状态过滤、批量审核、批量修复、批量重跑。
3. Assets 角色 / 场景 / 道具 tab 和 visual_lock / negative_prompt / locked 表单编辑。
4. Settings ComfyUI ping、FFmpeg check、IndexTTS command check、workflow JSON validation。
5. Preview final_manifest 读取、成片路径展示和可用时 video 标签预览。
6. tests 覆盖 settings、task runner、audio executor、final assembler、project actions、workflow store。
```

## 仍然需要 Codex 可继续优化的仓库任务

当前仓库内任务已经完成。后续增强应围绕真实项目体验继续迭代，但不能写死本地路径或真实 workflow node id。

## 必须本地完成

以下必须在用户本机完成，不要写死进仓库。

### ComfyUI

```text
1. 启动 ComfyUI。
2. 在 Settings 填 comfyui_url。
3. 上传真实 image/video workflow JSON。
4. 填写 workflow node mapping。
5. 测试 image/video executor。
```

### IndexTTS

```text
1. 安装并跑通 IndexTTS。
2. 确认 IndexTTS 推理脚本路径、模型路径、音色参数。
3. 在 Settings 配置 indextts_command。
4. 测试 audio executor。
```

IndexTTS 命令支持占位符：

```text
{text}
{text_file}
{output_file}
{voice_id}
{project_dir}
```

### FFmpeg

```text
1. 安装 FFmpeg。
2. 配置 ffmpeg_path。
3. 用真实 video clips 测试 final assembler。
```

## 最终验收

```text
1. 用户通过 UI 导入小说正文。
2. 点击 Run All 后生成 script/assets/storyboard/grid/audio/video/final task。
3. Settings 能上传 workflow JSON 并配置 node mapping。
4. Grid executor 能生成真实宫格 png。
5. ComfyUI executor 能解析真实输出路径。
6. IndexTTS command 配置后能生成 wav。
7. FFmpeg 配置后能合成 final.mp4。
8. Task 页面能查看错误日志。
9. Preview 页面能查看 final_manifest。
10. pytest 基础测试通过。
```
