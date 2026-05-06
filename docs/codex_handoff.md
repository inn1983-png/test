# Codex / 新对话接手说明

本文档用于让新的 ChatGPT 对话、本地 Codex、后续开发者快速理解本项目。

---

# 一、项目目标

本项目目标是搭建一套本地化、模块化、可长期迭代的 AI 短剧 / AI 漫剧生产系统。

核心流程：

```text
小说文本
↓
01 小说解析系统
↓
02 剧本改编系统
↓
03 角色库系统
04 场景库系统
05 道具库系统
↓
06 分镜系统
↓
07 分镜图生成系统
↓
08 音频系统
↓
09 视频生成系统
↓
10 成片拼接系统
```

---

# 二、最高架构原则

## 1. 一个文件夹就是一个独立系统

每个子系统只做一件事。

例如：

```text
01_novel_parser       只解析小说
02_script_writer      只改编剧本
03_character_library  只管理角色库
06_storyboard         只生成分镜
09_video              只生成视频
```

不要把多个系统的职责混在一起。

## 2. 子系统之间只通过文件交接

禁止一个模块直接 import 另一个模块的内部业务函数。

正确交接方式：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/events.json
↓
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
```

## 3. 代码和运行数据分离

模块文件夹保存代码、提示词、规则、schema。

正式运行数据统一进入：

```text
workspace/projects/{project_id}/
workspace/books/{book_id}/
```

## 4. 本地模型跑完必须释放显存

本项目默认所有模型都本地部署，包括：

- 本地 LLM
- 生图模型
- 生视频模型
- 视觉理解模型
- TTS / 音频模型

每个模块运行结束必须调用：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

即使模块失败，也必须在 `finally` 中释放资源。

## 5. 长篇小说必须使用全书共享资产库

长篇小说不能把角色、场景、道具资产放进单章目录。

必须使用：

```text
workspace/books/{book_id}/shared_assets/
```

单章运行数据放：

```text
workspace/books/{book_id}/chapters/{chapter_id}/
```

删除某一章时，只删除章节目录，不删除共享资产库。

---

# 三、短篇项目与长篇项目

## 短篇 / 单章项目

适合一次性视频、单章测试。

```text
workspace/projects/{project_id}/
```

## 长篇小说项目

适合连续章节、全书角色场景复用。

```text
workspace/books/{book_id}/
├─ shared_assets/      # 全书共享资产库
├─ global_memory/      # 全书长期记忆
└─ chapters/           # 每章运行数据
```

---

# 四、共享资产库

长篇小说共享资产库包括：

```text
shared_assets/
├─ characters/
│  ├─ characters.json
│  ├─ character_alias_map.json
│  └─ images/
├─ scenes/
│  ├─ scenes.json
│  ├─ scene_alias_map.json
│  └─ images/
├─ props/
│  ├─ props.json
│  ├─ prop_alias_map.json
│  └─ images/
└─ voice_library/
   ├─ voices.json
   └─ samples/
```

01 小说解析系统只提出新增候选资产。

03 / 04 / 05 资产库系统负责审核、合并、更新共享资产库。

---

# 五、每个模块的标准结构

每个模块文件夹建议包含：

```text
module_name/
├─ README.md              # 模块说明
├─ prompt.md              # 提示词
├─ rules.md               # 规则
├─ module_config.json     # 模块配置，首次运行自动生成
├─ run.py                 # 单模块入口
├─ src/                   # 业务代码，后续逐步增加
├─ schema/                # 输出结构定义，后续逐步增加
├─ input/                 # 仅用于单模块测试
└─ output/                # 仅用于单模块测试
```

正式运行不要长期写入模块 `output/`。

---

# 六、当前开发优先级

先搭总框架，再逐个打磨子系统。

推荐顺序：

```text
第一阶段：项目目录管理 + 01 小说解析系统
第二阶段：02 剧本改编系统
第三阶段：03/04/05 共享资产库系统
第四阶段：06 分镜系统
第五阶段：07 分镜图生成系统
第六阶段：08 音频系统
第七阶段：09 视频生成系统
第八阶段：10 成片拼接系统
```

---

# 七、开发时不要做的事

禁止：

- 把所有功能塞进一个巨大脚本
- 让 01 小说解析系统直接写剧本
- 让 02 剧本系统直接改角色库图片
- 让 06 分镜系统重新创造角色
- 把长篇角色资产放进单章目录
- 把模型权重、生成图片、视频、音频提交到 GitHub
- 让模块之间共享运行中的模型对象

---

# 八、当前最重要的方向

当前不是追求一键成片。

当前目标是先做到：

```text
每个子系统边界清晰
每个子系统输入输出清晰
每个子系统可以单独打磨
每个子系统跑完释放显存
每章数据可清理
长篇资产可复用
```

只要这个框架稳定，后面每个模块都可以逐步精修。
