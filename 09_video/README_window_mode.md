# 09_video 滑动窗口模式补充

本轮 09_video 已改为外部 Python 一段一提交。

## 核心定案

```text
ComfyUI 工作流每次只运行一组关键帧。
09_video 负责选择图片窗口、生成 prompt、注入节点、提交 ComfyUI、等待完成、断点续跑、最终合并。
不再依赖工作流内部三段 LLM 反推作为主提示词来源。
```

## 窗口模式

```text
4图模式：window_size=4, stride=3，窗口为 1-4, 4-7, 7-10 ...
6图模式：window_size=6, stride=5，窗口为 1-6, 6-11, 11-16 ...
9图模式：window_size=9, stride=8，窗口为 1-9, 9-17, 17-25 ...
```

环境变量：

```text
AI_DRAMA_VIDEO_KEYFRAME_WINDOW=4|6|9
AI_DRAMA_VIDEO_SEGMENT_SECONDS=10|12
```

## 每段 segment 字段

```text
segment_id
segment_index
window_mode
window_size
stride
frame_ids
image_paths
keyframe_details
anchor_frame_id
start_seconds
end_seconds
duration_seconds
output_clip_path
ltx_prompt
negative_prompt
motion_policy
```

## ComfyUI 多图注入节点

```text
AI_DRAMA_VIDEO_NODE_IMAGE_1=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_2=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_3=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_4=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_5=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_6=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_7=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_8=node_id:input_key
AI_DRAMA_VIDEO_NODE_IMAGE_9=node_id:input_key
AI_DRAMA_VIDEO_NODE_PROMPT=node_id:input_key
AI_DRAMA_VIDEO_NODE_NEGATIVE_PROMPT=node_id:input_key
AI_DRAMA_VIDEO_NODE_AUDIO_PATH=node_id:input_key
AI_DRAMA_VIDEO_NODE_DURATION=node_id:input_key
AI_DRAMA_VIDEO_NODE_OUTPUT_PREFIX=node_id:input_key
```

## prompt 来源

09 会优先读取：

```text
06_storyboard/storyboard.json
07_storyboard_image/image_manifest.json
08_audio/audio_timeline.json
```

然后为每个窗口自动生成：

```text
ltx_prompt
negative_prompt
motion_policy
```

prompt 单位是“一个窗口”，不是单张图。

## 测试

```bash
set AI_DRAMA_VIDEO_EXECUTION_MODE=dry_run
set AI_DRAMA_VIDEO_SEGMENT_SECONDS=10
set AI_DRAMA_VIDEO_KEYFRAME_WINDOW=4
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 09_video
```
