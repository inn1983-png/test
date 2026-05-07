# Web UI 总控工作台

`web_ui/` 不是临时测试页，而是整个 AI 短剧生产系统的最终版可视化控制台第一版。

它的目标是解决：LLM 长时间运行时用户看不到系统在做什么、每个阶段输出藏在 JSON 文件里、评分/返工/阻塞问题不直观、后续图片/音频/视频阶段难以统一管理。

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

## 当前已实现

### 1. 总览页

显示：

```text
pipeline.json 中的 01–10 模块顺序
当前任务状态
run_status.json 总状态
关键产物数量
最近项目列表
实时日志
```

### 2. 生产控制台

支持：

```text
project / book_chapter 模式
输入 project_id / book_id / chapter_id
粘贴 novel.txt 正文
从指定模块继续运行
只运行单个模块
配置本地 LLM Base URL / Model / Temperature / Timeout
启动生产
停止当前任务
```

### 3. 阶段透明区

自动读取：

```text
workspace/.../<module>/intermediate/*.json
```

并显示：

```text
阶段文件
stage_quality.score
stage_quality.passed
issues 数量
阶段 JSON 预览
```

适合 01–06 这种真实分阶段 LLM 模块。

### 4. 资产库入口

为最终版资产工作台预留并已接入：

```text
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
```

当前先做 JSON 预览，后续可升级成角色卡 / 场景卡 / 道具卡。

### 5. 产物中心

集中展示关键产物：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
06_storyboard/storyboard.json
06_storyboard/storyboard_meta.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
09_video/video_manifest.json
10_final_assembly/final.mp4
```

JSON 可直接弹窗预览。

---

## 最终版 UI 规划

### A. 项目首页

用于管理多个项目 / 多本书 / 多章节：

```text
项目列表
章节列表
当前进度
最近失败
最终成片
```

### B. 生产控制台

最终应支持：

```text
小说输入
章节选择
模块选择
本地 LLM 参数
ComfyUI 参数
CosyVoice2 参数
LTX2.3 参数
一键全流程
从失败处继续
只重跑某阶段
```

### C. 阶段透明区

每个阶段都要显示：

```text
阶段目标
输入摘要
LLM 原始输出
JSON 修复记录
评分
修改意见
自动重跑次数
最终输出
schema 校验
```

### D. 资产库工作台

03/04/05 后续升级成可视化资产卡：

```text
角色卡：canonical_name、fixed face、costume_variants、定妆照、造型照
场景卡：canonical_scene_name、scene_level、参考图、父场景
道具卡：canonical_prop_name、wearable_policy、绑定角色、参考图
```

### E. 分镜工作台

06 后续升级成真正分镜表：

```text
frame_id
剧情片段
角色引用
costume_id
appearance_asset_key
场景引用
道具引用
构图说明
连续性说明
四宫格预览组
```

07 图片生成后，分镜表应变成图文表格。

### F. 媒体生产区

07/08/09/10 后续接入：

```text
图片队列
音频队列
视频队列
显存资源状态
失败重试
文件预览
最终导出
```

### G. 返工中心

集中显示所有问题：

```text
needs_retry
retry_stages
upstream_blocking_issues
schema_validation_issues
quality_report.issues
```

最终目标是让用户不用翻 JSON，也能知道应该重跑 03、04、05 还是 06。

---

## 设计原则

```text
不是黑盒等待，而是过程可见。
不是单模块测试，而是 01–10 总控。
不是只看日志，而是看阶段产物、评分、返工原因。
不是临时页面，而是后续 07 图片、08 音频、09 视频、10 合成都能接入的最终工作台骨架。
```
