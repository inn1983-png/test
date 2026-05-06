# 项目运行目录规范

## 核心原则

代码模块不要堆积运行数据。

每一次小说处理、每一章处理、每一个视频项目，都应该生成一个独立的项目运行目录。

删除数据时，只需要删除对应项目目录。

---

## 推荐结构

```text
workspace/
└─ projects/
   └─ project_20260507_001/
      ├─ project_config.json
      ├─ input/
      │  └─ novel.txt
      │
      ├─ 01_novel_parser/
      │  ├─ paragraphs.json
      │  ├─ chunks.json
      │  ├─ novel_analysis.json
      │  ├─ events.json
      │  ├─ raw_characters.json
      │  ├─ raw_scenes.json
      │  ├─ raw_props.json
      │  ├─ conflict_map.json
      │  ├─ emotion_curve.json
      │  └─ module_handoff.json
      │
      ├─ 02_script_writer/
      │  ├─ script.json
      │  └─ script.txt
      │
      ├─ 03_character_library/
      │  ├─ characters.json
      │  └─ images/
      │
      ├─ 04_scene_library/
      │  ├─ scenes.json
      │  └─ images/
      │
      ├─ 05_prop_library/
      │  ├─ props.json
      │  └─ images/
      │
      ├─ 06_storyboard/
      │  ├─ storyboard.json
      │  └─ storyboard.csv
      │
      ├─ 07_storyboard_image/
      │  └─ images/
      │
      ├─ 08_audio/
      │  ├─ audio_script.json
      │  └─ final_audio.wav
      │
      ├─ 09_video/
      │  └─ clips/
      │
      └─ 10_final_assembly/
         ├─ final.mp4
         ├─ cover.png
         └─ subtitles.srt
```

---

## 为什么不建议直接写入各模块自己的 output/

模块目录里的 `output/` 适合做：

- 单模块测试
- 临时调试
- 示例输出

但正式项目不应该长期堆在模块目录。

否则会出现：

```text
01_novel_parser/output/堆满不同小说的数据
02_script_writer/output/堆满不同章节的数据
07_storyboard_image/output/堆满大量图片
09_video/output/堆满大量视频
```

后期很难清理，也很难知道哪些文件属于同一个项目。

---

## 正式运行规则

正式运行时，每个模块都写入：

```text
workspace/projects/{project_id}/{module_name}/
```

例如：

```text
workspace/projects/project_20260507_001/01_novel_parser/novel_analysis.json
workspace/projects/project_20260507_001/02_script_writer/script.json
workspace/projects/project_20260507_001/06_storyboard/storyboard.json
workspace/projects/project_20260507_001/09_video/clips/clip_001.mp4
```

---

## 模块调用规则

后一个模块读取前一个模块的项目目录产出。

例如：

```text
02_script_writer 读取：
workspace/projects/{project_id}/01_novel_parser/novel_analysis.json

03_character_library 读取：
workspace/projects/{project_id}/01_novel_parser/raw_characters.json

06_storyboard 读取：
workspace/projects/{project_id}/02_script_writer/script.json
workspace/projects/{project_id}/03_character_library/characters.json
workspace/projects/{project_id}/04_scene_library/scenes.json
workspace/projects/{project_id}/05_prop_library/props.json
```

---

## 清理规则

删除一个项目全部运行数据：

```text
删除 workspace/projects/{project_id}/
```

删除后不会影响：

- 模块代码
- 提示词
- 规则文件
- schema 文件
- 其他项目数据

---

## 最高原则

```text
模块文件夹 = 系统代码
workspace/projects/{project_id} = 单个项目数据
```

不要把长期运行数据堆在模块文件夹里。
