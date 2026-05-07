# Web UI 总控工作台

`web_ui/` 不是临时测试页，而是整个 AI 短剧生产系统的最终版可视化控制台第一版。

它现在已经接入 00–10：

```text
00_main_controller：总控 / 自检 / 数据链路检查
01_novel_parser：小说解析
02_script_writer：剧本改编
03_character_system：角色资产库
04_scene_system：场景资产库
05_prop_system：道具资产库
06_storyboard：单帧分镜
07_storyboard_image：分镜图片
08_audio：音频生成
09_video：视频生成
10_final_assembly：最终成片包装
```

UI 的目标是解决：LLM 长时间运行时用户看不到系统在做什么、每个阶段输出藏在 JSON 文件里、评分/返工/阻塞问题不直观、图片/音频/视频/最终合成难以统一管理。

---

## 启动方式

在项目根目录运行：

```bash
python web_ui/server.py --host 127.0.0.1 --port 1144
```

也可以直接使用默认端口启动：

```bash
python web_ui/server.py
```

浏览器打开：

```text
http://127.0.0.1:1144
```

---

## 推荐检查顺序

进入 UI 后，建议先在「生产控制台」依次执行：

```text
1. 00–10 数据链路检查
2. 00 总控自检
3. 全流程 dry-run
4. 启动 01–10 生产 / 或只跑指定模块
```

对应命令行：

```bash
python 00_main_controller/check_data_link.py --project-id ui_data_link_check
python 00_main_controller/self_check.py --keep
python 00_main_controller/run_pipeline.py --mode project --project-id ui_dry_run_check --dry-run --strict-order
```

数据链路检查报告输出：

```text
workspace/projects/{project_id}/00_data_link_check_report.json
```

该检查只做结构和链路检查，不调用 LLM、不调用 ComfyUI、不调用 IndexTTS、不调用 LTX、不调用 FFmpeg。

---

## 当前已实现

### 1. 生产驾驶舱

显示：

```text
00–10 显示链路
当前任务状态
run_status.json 总状态
关键产物数量
最近项目列表
实时日志
链路检查摘要
```

### 2. 生产控制台

支持：

```text
00–10 数据链路检查
00 总控自检
全流程 dry-run
只建运行上下文
project / book_chapter 模式
输入 project_id / book_id / chapter_id
粘贴 novel.txt 正文
从指定模块继续运行
只运行单个模块
配置本地 LLM Base URL / Model / Temperature / Timeout
配置 07 图片执行模式 / ComfyUI 地址 / workflow mapping / 风格后缀 / 负向提示词
配置 08 音频执行模式 / IndexTTS 根目录
配置 09 视频执行模式
配置 10/09 使用的 FFmpeg 路径
启动生产
停止当前任务
```

### 3. 阶段透明区

自动读取：

```text
workspace/.../<module>/intermediate/*.json
workspace/projects/{project_id}/00_data_link_check_report.json
```

并显示：

```text
00 链路检查结果
阶段文件
stage_quality.score
stage_quality.passed
issues 数量
阶段 JSON 预览
```

### 4. 返工中心

集中显示：

```text
模块 failed / blocked
阶段低分 / issues
quality_report.needs_retry
schema_validation_issues
00 数据链路失败项
```

### 5. 资产库入口

已接入：

```text
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
```

当前支持 JSON 预览和提示词草稿编辑，后续可升级成角色卡 / 场景卡 / 道具卡的真实编辑与单项重绘。

### 6. 图片阶段入口

已接入 07 相关预览入口：

```text
07_storyboard_image/image_manifest.json
07_storyboard_image/dependency_index.json
角色定妆图
角色造型图
场景 / 道具参考图
正式单帧分镜图
```

### 7. 分镜工作台

读取：

```text
06_storyboard/storyboard.json
```

显示分镜卡片，并为后续单帧重绘预留提示词编辑入口。

### 8. 产物中心

集中展示关键产物：

```text
00_data_link_check_report.json
runtime_context.json
manifest.json
run_status.json
01_novel_parser/novel_analysis.json
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
06_storyboard/storyboard.json
06_storyboard/storyboard_meta.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
08_audio/audio_timeline.json
08_audio/subtitle.srt
08_audio/subtitle.ass
09_video/video_manifest.json
09_video/final_video.mp4
10_final_assembly/final.mp4
10_final_assembly/final_manifest.json
10_final_assembly/final_meta.json
```

JSON、字幕、图片、音频、视频文件都能通过 UI 预览或定位。

---

## 设计原则

```text
不是黑盒等待，而是过程可见。
不是单模块测试，而是 00–10 总控。
不是只看日志，而是看阶段产物、评分、返工原因。
00 只做总控、上下文、校验、自检和数据链路检查。
01–10 仍按 pipeline.json 执行，模块边界不改变。
```
