# AI Short Drama Agent Canvas + UI Refactor Plan

## 一、改造目标

当前项目是模块化流水线结构：

```text
风格圣经 → 小说 → 剧本 → 角色库/场景库/道具库 → 分镜 → 分镜图 → 音频 → 视频 → 成片
```

仓库 README 当前仍然是以 `00_style_system` 到 `10_final_assembly` 为核心的模块化骨架，并由 `00_main_controller` 串联执行。

本次改造目标是：

```text
从“模块流水线”
改成
“Agent Canvas 短剧生产工作台”
```

最终核心变成：

```text
Canvas 状态机
+ Agent 调度
+ Executor 执行
+ UI 画布工作台
+ ComfyUI 本地生产
```

---

# 二、参考项目吸收点

## 1. 参考 ArcReel

ArcReel 的核心是“从小说到短视频，全程 AI Agent 驱动”，流程包含小说、角色/线索、剧本 JSON、分镜图/宫格图、视频片段、FFmpeg 合成。

重点参考：

```text
AI Agent 工作流
多供应商图片/视频生成
异步任务队列
可视化工作台
项目管理
素材预览
版本回滚
实时任务追踪
宫格模式 grid_4 / grid_6 / grid_9
```

尤其要参考它的：

```text
多个分镜合成为宫格图
宫格图拆分后作为首尾帧驱动视频生成
```

ArcReel README 明确提到支持 `grid_4 / grid_6 / grid_9` 宫格模式。

---

## 2. 参考 AIComicBuilder

AIComicBuilder 的流程是：

```text
剧本输入 → 剧本解析 → 角色提取 → 角色四视图 → 智能分镜 → 首尾帧生成 → 视频提示词 → 视频生成 → 视频合成 + 字幕
```

它还支持分镜编辑抽屉、角色内联面板、看板视图、单张分镜精细编辑。

重点参考：

```text
项目列表页
剧本导入页
角色管理页
分镜看板页
看板详情页
提示词管理页
模型配置页
分镜 AI 优化入口
```

AIComicBuilder 的 UI 最值得参考的是：

```text
分镜不是单纯 JSON，而是可视化卡片
每个镜头可以单独编辑
每个阶段可以单独触发
用户可以控制流水线节奏
```

---

## 3. 参考 AgentCine

AgentCine 的核心是 AI 影视创作工作台，包含文本分析、角色与场景资产管理、分镜生成、配音、视频任务编排、素材库、配置中心、BullMQ Worker、Watchdog、MinIO/S3 存储。

重点参考：

```text
任务队列面板
后台 Worker
Watchdog
素材库
项目工作区
模型配置中心
Agent Pipeline Dashboard
任务状态流转
```

AgentCine 还把 Agent 分成两种模式：

```text
Agent Sessions：对话式，自主决策
Agent Pipeline：确定性图执行
```

这个非常适合本项目。

---

# 三、最终系统定位

最终项目不是纯后端脚本，也不是单纯 ComfyUI 工作流。

最终定位：

```text
本地 AI 短剧 / 漫剧生产工作台
```

核心能力：

```text
1. 小说导入
2. Agent 自动拆解
3. 画布式分镜
4. 角色 / 场景 / 道具资产管理
5. 单镜头提示词管理
6. 宫格分镜生成
7. 音频驱动视频
8. ComfyUI 本地执行
9. 局部失败返工
10. 成片合成
```

---

# 四、最终目录结构

```text
AI_ShortDrama_Agent_System/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ canvas_store.py
│  │  ├─ node_store.py
│  │  ├─ project_store.py
│  │  ├─ task_store.py
│  │  └─ status.py
│  │
│  ├─ schemas/
│  │  ├─ canvas.schema.json
│  │  ├─ node.schema.json
│  │  ├─ source_text.schema.json
│  │  ├─ story_segment.schema.json
│  │  ├─ script_block.schema.json
│  │  ├─ asset.schema.json
│  │  ├─ shot.schema.json
│  │  ├─ storyboard_grid.schema.json
│  │  ├─ audio_segment.schema.json
│  │  ├─ video_clip.schema.json
│  │  ├─ task.schema.json
│  │  └─ agent_output.schema.json
│  │
│  ├─ agents/
│  │  ├─ director_agent.py
│  │  ├─ writer_agent.py
│  │  ├─ asset_agent.py
│  │  ├─ storyboard_agent.py
│  │  ├─ reviewer_agent.py
│  │  └─ repair_agent.py
│  │
│  ├─ executors/
│  │  ├─ image_executor.py
│  │  ├─ grid_executor.py
│  │  ├─ audio_executor.py
│  │  ├─ comfyui_executor.py
│  │  ├─ video_executor.py
│  │  ├─ final_assembler.py
│  │  └─ watchdog_executor.py
│  │
│  ├─ workers/
│  │  ├─ task_runner.py
│  │  ├─ image_worker.py
│  │  ├─ audio_worker.py
│  │  ├─ video_worker.py
│  │  └─ watchdog.py
│  │
│  └─ prompts/
│     ├─ style/
│     ├─ writer/
│     ├─ asset/
│     ├─ storyboard/
│     ├─ reviewer/
│     └─ repair/
│
├─ frontend/
│  ├─ src/
│  │  ├─ app/
│  │  ├─ pages/
│  │  ├─ components/
│  │  ├─ layouts/
│  │  ├─ stores/
│  │  ├─ api/
│  │  └─ styles/
│  └─ package.json
│
├─ projects/
│  └─ demo_project/
│     ├─ canvas.json
│     ├─ source/
│     ├─ nodes/
│     ├─ assets/
│     │  ├─ characters/
│     │  ├─ scenes/
│     │  └─ props/
│     ├─ images/
│     ├─ grids/
│     ├─ audio/
│     ├─ videos/
│     ├─ manifests/
│     ├─ history/
│     └─ final/
│
├─ legacy/
│  ├─ 00_style_system/
│  ├─ 00_main_controller/
│  ├─ 00_common/
│  ├─ 01_novel_parser/
│  ├─ 02_script_writer/
│  ├─ 03_character_system/
│  ├─ 04_scene_system/
│  ├─ 05_prop_system/
│  ├─ 06_storyboard/
│  ├─ 07_storyboard_image/
│  ├─ 08_audio/
│  ├─ 09_video/
│  └─ 10_final_assembly/
│
├─ docs/
│  └─ AGENT_CANVAS_UI_REFACTOR_PLAN.md
│
├─ requirements.txt
└─ run.py
```

---

# 五、后端核心架构

## 1. Canvas 状态机

`canvas.json` 只保存轻量索引：

```json
{
  "project_id": "demo_project",
  "chapter_id": "chapter_001",
  "style_id": "ancient_live_action_realistic",
  "status": "in_progress",
  "current_stage": "storyboard",
  "nodes": [
    {
      "id": "shot_001",
      "type": "shot",
      "status": "waiting_image",
      "file": "nodes/shot_001.json"
    },
    {
      "id": "grid_001",
      "type": "storyboard_grid",
      "status": "waiting_build",
      "file": "nodes/grid_001.json"
    }
  ],
  "edges": [
    ["shot_001", "grid_001"],
    ["grid_001", "video_001"]
  ]
}
```

具体内容放在：

```text
nodes/*.json
```

---

## 2. Node 类型

只保留 10 种：

```text
source_text
story_segment
script_block
character_asset
scene_asset
prop_asset
shot
storyboard_grid
audio_segment
video_clip
```

不要继续无限扩展节点类型。

---

## 3. Agent 分工

```text
director_agent      总导演，判断下一步
writer_agent        小说解析 + 剧本 + 粗分镜
asset_agent         角色 + 场景 + 道具资产
storyboard_agent    正式分镜 + 提示词 + 宫格分组
reviewer_agent      质量检查
repair_agent        局部返工
```

---

## 4. Executor 分工

```text
image_executor       生图
grid_executor        拼宫格
audio_executor       配音 + 字幕
comfyui_executor     调 ComfyUI 并等待完成
video_executor       视频片段生成
final_assembler      FFmpeg 合成
watchdog_executor    卡死检测 / 超时检测
```

---

# 六、UI 总体设计

## UI 定位

UI 不做成复杂专业剪辑软件。

UI 目标是：

```text
让用户看得懂当前项目进度
能看到每个分镜状态
能手动改坏掉的镜头
能局部重跑
能管理角色 / 场景 / 道具资产
能看到 ComfyUI 任务是否完成
```

---

# 七、UI 页面结构

最终前端建议分 8 个主页面。

```text
1. 项目首页 Dashboard
2. 项目工作台 Project Workspace
3. 小说 / 剧本页 Script Editor
4. 资产库 Asset Hub
5. 分镜画布 Storyboard Canvas
6. 生成任务中心 Task Center
7. 成片预览 Preview
8. 设置 Settings
```

---

# 八、页面一：项目首页 Dashboard

## 功能

参考 ArcReel / AIComicBuilder 的项目列表页。

显示：

```text
项目封面
项目名称
当前章节
当前进度
生成状态
最后更新时间
失败任务数量
最终视频入口
```

## 卡片字段

```json
{
  "project_id": "demo_project",
  "title": "捕快的黑道人生",
  "cover": "final/cover.png",
  "status": "in_progress",
  "current_stage": "storyboard_image",
  "progress": 62,
  "failed_tasks": 2,
  "updated_at": ""
}
```

## UI 布局

```text
左侧：项目列表
顶部：新建项目 / 导入项目 / 设置
中间：项目卡片网格
右侧：最近任务 / 失败提醒
```

---

# 九、页面二：项目工作台 Project Workspace

这是主页面。

## 布局

```text
顶部：项目名称 + 当前阶段 + 运行按钮 + 暂停按钮 + 导出按钮
左侧：阶段导航
中间：当前阶段内容
右侧：Agent 助手 / 当前节点详情
底部：任务进度条
```

## 阶段导航

```text
1. 风格
2. 小说
3. 剧本
4. 资产
5. 分镜
6. 图片
7. 音频
8. 视频
9. 成片
```

## 状态颜色

```text
灰色：未开始
蓝色：等待中
黄色：生成中
绿色：完成
红色：失败
紫色：需要人工确认
```

---

# 十、页面三：小说 / 剧本页 Script Editor

## 参考

参考 AIComicBuilder 的剧本导入、剧本生成、角色解析流程。

## 功能

```text
上传 TXT / DOCX / PDF
显示原文
显示 Agent 拆出的 story_segment
显示剧本 script_block
支持手动编辑对白 / OS / 留白
支持重新生成当前段
支持锁定某段不再修改
```

## 三栏布局

```text
左栏：原文
中栏：剧本
右栏：Agent 分析 / 高刺激点 / 保留原文句子
```

## 剧本块 UI

每个 `script_block` 显示成卡片：

```text
段落标题
剧情功能：压迫 / 反击 / 转折 / 爆点 / 留钩子
对白
OS
画面动作
节奏备注
状态
```

---

# 十一、页面四：资产库 Asset Hub

## 参考

参考 AgentCine 的全局素材库与项目素材复用。

## 资产类型

```text
角色
场景
道具
声音
风格参考图
```

## 角色卡片

显示：

```text
角色名
性别
身份
视觉锁定词
服装锁定词
参考图
出现镜头数量
是否已锁定
```

## 场景卡片

显示：

```text
场景名
时代
光照
布局
禁止元素
出现镜头数量
参考图
```

## 道具卡片

显示：

```text
道具名
用途
视觉锁定
出现镜头
参考图
```

## 关键功能

```text
重新生成角色参考图
上传替代参考图
锁定角色
合并重复角色
查看该角色出现的全部 shot
```

这一步对你非常重要，因为你最怕：

```text
串脸
性别错
同一角色变老变年轻
道具污染画面
```

---

# 十二、页面五：分镜画布 Storyboard Canvas

这是整个项目最重要的 UI。

## 参考

参考 Toonflow 的画布思路、AIComicBuilder 的分镜看板、ArcReel 的宫格逻辑。

## 分镜画布不是普通列表

它应该有三种视图：

```text
1. Timeline 时间线视图
2. Board 看板视图
3. Grid 宫格视图
```

---

## 1. Timeline 时间线视图

按剧情顺序显示所有 shot。

每个 shot 是一张卡片：

```text
shot 编号
cap
画面缩略图
角色标签
场景标签
道具标签
状态
评分
失败原因
```

适合看剧情连续性。

---

## 2. Board 看板视图

参考 AIComicBuilder 的看板页。

按状态分列：

```text
待生成提示词
待生图
生图中
图片完成
待拼宫格
待生成视频
视频完成
失败
```

每个 shot 可以拖拽移动，或者点击重跑。

---

## 3. Grid 宫格视图

参考 ArcReel 的 `grid_4 / grid_6 / grid_9`。

显示：

```text
grid_001
包含 shot_001 - shot_004
宫格预览图
视频状态
对应音频段
LTX / ComfyUI 任务状态
```

默认策略：

```text
优先 grid_4
同一 grid 内保持同场景、同光源、同服装
grid_6 / grid_9 只用于环境铺陈或动作连续
```

---

## Shot 详情抽屉

点击任意 shot，右侧弹出详情抽屉。

内容：

```text
cap 原文
对白
OS
角色
场景
道具
镜头语言
图片提示词
负向提示词
视频提示词
生成图片
审查结果
失败原因
重跑按钮
锁定按钮
```

按钮：

```text
重新生成提示词
重新生成图片
重新加入宫格
重新生成视频
标记通过
锁定该镜头
```

---

# 十三、页面六：生成任务中心 Task Center

## 参考

参考 AgentCine 的 Bull Board / Worker / Watchdog 思路。

## 功能

显示所有任务：

```text
任务 ID
节点 ID
任务类型
执行器
状态
耗时
重试次数
错误日志
输出文件
```

## 任务状态

```text
pending
running
done
failed
timeout
cancelled
```

## 任务类型

```text
writer_generate
asset_generate
storyboard_generate
image_generate
grid_build
audio_generate
video_generate
final_assemble
review
repair
```

## 操作

```text
重试任务
取消任务
查看日志
打开输出文件
定位到对应节点
```

---

# 十四、页面七：成片预览 Preview

## 功能

```text
预览最终视频
预览每个 video_clip
查看字幕
查看音频波形
查看视频片段列表
重新合成
导出 final.mp4
导出全部素材包
```

## 布局

```text
左侧：视频播放器
右侧：clip 列表
底部：字幕 / 时间轴
```

---

# 十五、页面八：设置 Settings

## 设置项

```text
模型配置
ComfyUI 地址
图片生成工作流
视频生成工作流
CosyVoice2 配置
FFmpeg 路径
默认风格
默认宫格模式
默认视频时长
失败重试次数
任务超时时间
```

## ComfyUI 设置

```json
{
  "comfyui_url": "http://127.0.0.1:8188",
  "image_workflow": "workflows/image_storyboard.json",
  "video_workflow": "workflows/ltx23_grid_video.json",
  "wait_until_complete": true,
  "timeout_seconds": 1800,
  "max_retry": 3
}
```

---

# 十六、UI 组件设计

## 基础组件

```text
ProjectCard
StageProgress
StatusBadge
NodeCard
ShotCard
AssetCard
GridCard
TaskRow
AgentChatPanel
PromptEditor
MediaPreview
ReviewScore
ErrorPanel
```

---

## ShotCard

```text
顶部：shot_001 + 状态
中间：分镜图缩略图
下方：cap 简短文本
标签：角色 / 场景 / 道具
右下角：评分 / 失败标记
```

---

## GridCard

```text
顶部：grid_001 / grid_4
中间：宫格预览图
下方：shot_001 - shot_004
右侧：生成视频按钮
状态：waiting_video / running / done / failed
```

---

## AgentChatPanel

右侧常驻。

显示：

```text
当前 Agent 正在做什么
下一步建议
失败原因
可执行操作
```

用户可以输入：

```text
重做 shot_037
把这个角色变年轻一点
这个场景不要现代家具
重新生成 grid_008
只重跑失败视频
```

但第一版可以先不做复杂对话，只做按钮式 Agent 操作。

---

# 十七、UI 颜色与风格

建议 UI 风格：

```text
暗色为主
卡片式布局
少用花哨动效
重点突出状态
适合长时间制作观看
```

颜色：

```text
背景：深灰 / 黑灰
主色：蓝紫色
成功：绿色
警告：黄色
失败：红色
等待：灰色
运行中：蓝色
锁定：紫色
```

视觉原则：

```text
不要像剪辑软件那么复杂
不要像纯后台那么枯燥
要像“AI 制作控制台”
```

---

# 十八、前端技术建议

如果你想简单快速：

```text
React + Vite + TypeScript + Tailwind + Zustand
```

如果你想后续做成完整产品：

```text
Next.js + TypeScript + Tailwind + Zustand
```

我建议当前项目先用：

```text
Vite + React + TypeScript
```

理由：

```text
启动快
结构轻
适合本地工具
不用先搞复杂服务端渲染
```

---

# 十九、API 设计

## 项目 API

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

## Canvas API

```text
GET  /api/projects/{project_id}/canvas
POST /api/projects/{project_id}/canvas/step
POST /api/projects/{project_id}/canvas/run
POST /api/projects/{project_id}/canvas/pause
```

## Node API

```text
GET    /api/projects/{project_id}/nodes/{node_id}
PATCH  /api/projects/{project_id}/nodes/{node_id}
POST   /api/projects/{project_id}/nodes/{node_id}/rerun
POST   /api/projects/{project_id}/nodes/{node_id}/review
POST   /api/projects/{project_id}/nodes/{node_id}/lock
```

## Task API

```text
GET  /api/projects/{project_id}/tasks
POST /api/projects/{project_id}/tasks/{task_id}/retry
POST /api/projects/{project_id}/tasks/{task_id}/cancel
```

## Asset API

```text
GET   /api/projects/{project_id}/assets
PATCH /api/projects/{project_id}/assets/{asset_id}
POST  /api/projects/{project_id}/assets/{asset_id}/regenerate
```

## Media API

```text
GET /media/{project_id}/images/{filename}
GET /media/{project_id}/videos/{filename}
GET /media/{project_id}/audio/{filename}
```

---

# 二十、任务队列第一版

第一版不用 Redis。

使用文件队列：

```text
tasks/
├─ pending/
├─ running/
├─ done/
└─ failed/
```

任务文件：

```json
{
  "task_id": "task_video_001",
  "node_id": "video_001",
  "task_type": "video_generate",
  "executor": "video_executor",
  "status": "pending",
  "retry_count": 0,
  "max_retry": 3,
  "created_at": "",
  "updated_at": ""
}
```

后续再升级：

```text
SQLite → Redis → Celery / BullMQ
```

---

# 二十一、改造阶段

## 第一阶段：加 Canvas + Node 层

新增：

```text
backend/app/canvas_store.py
backend/app/node_store.py
backend/schemas/
projects/demo_project/
```

实现：

```text
创建 canvas.json
创建 nodes/*.json
更新节点状态
记录 history
旧模块输出迁移为 canvas 节点
```

---

## 第二阶段：加基础 UI

先做 4 个页面：

```text
项目首页
项目工作台
分镜画布
任务中心
```

第一版 UI 不追求漂亮，先能用：

```text
能看到节点
能看到状态
能点击重跑
能打开 shot 详情
能看到任务失败原因
```

---

## 第三阶段：Director Agent 接管调度

新增：

```text
backend/agents/director_agent.py
```

替代旧的：

```text
00_main_controller/run_pipeline.py
```

但旧 controller 暂时保留在 `legacy/`。

---

## 第四阶段：合并 Writer Agent

合并：

```text
01_novel_parser
02_script_writer
06_storyboard 的粗分镜部分
```

变成：

```text
backend/agents/writer_agent.py
```

---

## 第五阶段：合并 Asset Agent

合并：

```text
03_character_system
04_scene_system
05_prop_system
```

变成：

```text
backend/agents/asset_agent.py
```

---

## 第六阶段：重做 Storyboard Canvas

新增：

```text
backend/agents/storyboard_agent.py
backend/executors/grid_executor.py
frontend/src/pages/StoryboardCanvas.tsx
frontend/src/components/ShotCard.tsx
frontend/src/components/GridCard.tsx
frontend/src/components/ShotDetailDrawer.tsx
```

目标：

```text
shot 卡片化
grid 可视化
状态可视化
局部重跑
```

---

## 第七阶段：执行器接管生产

新增：

```text
backend/executors/image_executor.py
backend/executors/audio_executor.py
backend/executors/comfyui_executor.py
backend/executors/video_executor.py
backend/executors/final_assembler.py
```

---

## 第八阶段：Reviewer + Repair

新增：

```text
backend/agents/reviewer_agent.py
backend/agents/repair_agent.py
```

UI 增加：

```text
评分
问题列表
修复建议
一键修复
```

---

# 二十二、最终运行逻辑

```text
1. 用户创建项目
2. 导入小说
3. writer_agent 生成剧情段、剧本、粗分镜
4. asset_agent 生成角色、场景、道具
5. storyboard_agent 生成 shot 和 grid
6. UI 显示分镜画布
7. image_executor 生成分镜图
8. grid_executor 拼宫格
9. audio_executor 生成配音和字幕
10. video_executor 调 ComfyUI 生成视频
11. reviewer_agent 检查
12. repair_agent 修失败节点
13. final_assembler 合成最终视频
14. UI 预览和导出
```

---

# 二十三、最终验收标准

## 后端验收

```text
能创建项目
能生成 canvas.json
能生成 nodes/*.json
能更新节点状态
能局部重跑节点
ComfyUI 执行器能等待任务完成
失败任务能进入 failed
Watchdog 能识别卡死任务
```

---

## Agent 验收

```text
writer_agent 不会把长文压缩过狠
asset_agent 不会重复拆角色
storyboard_agent 的 cap 严格来自原文连续片段
reviewer_agent 能指出画面问题
repair_agent 只修失败节点
director_agent 能判断下一步
```

---

## UI 验收

```text
能看到项目列表
能看到项目当前阶段
能看到分镜卡片
能看到宫格卡片
能打开 shot 详情
能编辑 prompt
能重跑单个 shot
能查看任务状态
能查看失败原因
能预览最终视频
```

---

# 二十四、最终结论

本项目最终应改成：

```text
Agent Canvas 短剧生产工作台
```

不是：

```text
传统模块流水线
```

最终核心：

```text
Canvas 负责状态
Node 负责内容
Agent 负责判断
Executor 负责执行
UI 负责可视化和人工干预
Reviewer 负责检查
Repair 负责局部返工
```

一句话：

```text
用 Canvas 管住全局，用 Agent 减少流程复杂度，用 UI 让每个分镜、宫格、任务都能看见、能编辑、能重跑。
```
