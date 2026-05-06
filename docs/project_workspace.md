# 项目运行目录规范

## 核心原则

代码模块不要堆积运行数据。

短篇或单章项目，可以使用一个独立项目运行目录。

长篇小说项目，必须拆成：

```text
全书共享资产库 + 单章运行目录
```

删除单章数据时，只删除章节运行目录；不要删除全书共享资产库。

---

# 一、短篇 / 单章项目结构

适合：

- 单篇故事
- 单章测试
- 一次性视频
- 模块调试

```text
workspace/
└─ projects/
   └─ project_20260507_001/
      ├─ project_config.json
      ├─ input/
      │  └─ novel.txt
      │
      ├─ 01_novel_parser/
      ├─ 02_script_writer/
      ├─ 03_character_library/
      ├─ 04_scene_library/
      ├─ 05_prop_library/
      ├─ 06_storyboard/
      ├─ 07_storyboard_image/
      ├─ 08_audio/
      ├─ 09_video/
      └─ 10_final_assembly/
```

短篇项目中，角色、场景、道具可以直接放在该项目目录下。

---

# 二、长篇小说项目结构

适合：

- 长篇小说
- 连续剧集
- 多章节连续生产
- 同一批角色/场景/道具需要反复复用

推荐结构：

```text
workspace/
└─ books/
   └─ book_001/
      ├─ book_config.json
      ├─ source/
      │  ├─ full_novel.txt
      │  └─ chapters/
      │     ├─ chapter_001.txt
      │     ├─ chapter_002.txt
      │     └─ chapter_003.txt
      │
      ├─ shared_assets/
      │  ├─ characters/
      │  │  ├─ characters.json
      │  │  ├─ character_alias_map.json
      │  │  └─ images/
      │  │     ├─ char_001_front.png
      │  │     └─ char_001_reference.png
      │  │
      │  ├─ scenes/
      │  │  ├─ scenes.json
      │  │  ├─ scene_alias_map.json
      │  │  └─ images/
      │  │     ├─ scene_001.png
      │  │     └─ scene_002.png
      │  │
      │  ├─ props/
      │  │  ├─ props.json
      │  │  ├─ prop_alias_map.json
      │  │  └─ images/
      │  │     ├─ prop_001.png
      │  │     └─ prop_002.png
      │  │
      │  └─ voice_library/
      │     ├─ voices.json
      │     └─ samples/
      │
      ├─ global_memory/
      │  ├─ book_summary.json
      │  ├─ relationship_map.json
      │  ├─ timeline_global.json
      │  ├─ unresolved_clues.json
      │  └─ style_bible.md
      │
      └─ chapters/
         ├─ chapter_001/
         │  ├─ chapter_config.json
         │  ├─ input/
         │  │  └─ novel.txt
         │  ├─ 01_novel_parser/
         │  ├─ 02_script_writer/
         │  ├─ 06_storyboard/
         │  ├─ 07_storyboard_image/
         │  ├─ 08_audio/
         │  ├─ 09_video/
         │  └─ 10_final_assembly/
         │
         └─ chapter_002/
            ├─ chapter_config.json
            ├─ input/
            └─ ...
```

---

# 三、长篇小说的目录分工

## 1. `shared_assets/`

全书共享资产库。

这里保存长期复用的内容：

- 角色库
- 场景库
- 道具库
- 角色图
- 场景图
- 道具图
- 音色库

这些内容不应该放在单章目录里。

单章目录可以引用它们，但不能随便覆盖它们。

## 2. `chapters/chapter_xxx/`

单章运行目录。

这里保存某一章临时或成片相关数据：

- 本章小说文本
- 本章解析结果
- 本章剧本
- 本章分镜
- 本章分镜图
- 本章音频
- 本章视频片段
- 本章最终成片

删除某一章数据时，只删除：

```text
workspace/books/{book_id}/chapters/{chapter_id}/
```

不会影响：

```text
workspace/books/{book_id}/shared_assets/
```

## 3. `global_memory/`

全书长期记忆。

这里保存跨章节需要继承的信息：

- 全书剧情摘要
- 全局时间线
- 人物关系网
- 未解决伏笔
- 世界观设定
- 文风设定
- 禁止改动的核心设定

---

# 四、长篇小说模块调用规则

## 01 小说解析系统

输入：

```text
workspace/books/{book_id}/chapters/{chapter_id}/input/novel.txt
workspace/books/{book_id}/global_memory/book_summary.json
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/props/props.json
```

输出：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/
```

同时输出本章发现的新增候选资产：

```text
new_character_candidates.json
new_scene_candidates.json
new_prop_candidates.json
```

注意：01 只提出候选，不直接覆盖全书共享资产库。

## 03 / 04 / 05 资产库系统

资产库系统负责把本章候选资产合并进全书共享资产库。

输入：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/new_character_candidates.json
workspace/books/{book_id}/shared_assets/characters/characters.json
```

输出：

```text
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/characters/character_alias_map.json
```

场景库、道具库同理。

## 06 分镜系统

分镜系统读取本章剧本，同时引用全书共享资产库：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/props/props.json
```

---

# 五、清理规则

## 删除某一章运行数据

```text
删除 workspace/books/{book_id}/chapters/{chapter_id}/
```

不会影响角色、场景、道具资产。

## 删除整本书项目

```text
删除 workspace/books/{book_id}/
```

会删除该书所有章节、共享资产、全局记忆。

## 删除单次短篇项目

```text
删除 workspace/projects/{project_id}/
```

---

# 六、模块文件夹与运行数据的关系

```text
模块文件夹 = 系统代码
workspace/projects/{project_id} = 短篇/单章项目数据
workspace/books/{book_id} = 长篇小说项目数据
workspace/books/{book_id}/shared_assets = 全书共享资产库
workspace/books/{book_id}/chapters/{chapter_id} = 单章运行数据
```

---

# 七、最高原则

不要把长期运行数据堆在模块文件夹里。

不要把全书共享资产放进单章目录里。

长篇小说必须区分：

```text
可删除的单章运行数据
不可随便删除的全书共享资产
```
