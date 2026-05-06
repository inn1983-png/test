# 产物存储与查找规范：SQLite + 轻量 manifest

## 核心结论

不能把所有产物都塞进一个巨大的 `manifest.json`。

正式方案：

```text
artifacts.db   # SQLite，记录详细产物，方便查询
manifest.json  # 轻量摘要，只记录统计和关键入口文件
```

这样既不会让 JSON 膨胀，又方便后续模块快速查找上一步产物。

---

# 一、为什么不能只用 manifest.json

长篇小说项目里，产物数量会非常多。

例如：

```text
每章 80 张分镜图
每章 20 段视频
100 章 = 8000 张图 + 2000 段视频
```

如果所有内容都写入一个 JSON，会出现：

- 文件越来越大
- 每次读写都要加载完整 JSON
- 查询慢
- 容易写坏
- 不方便 Codex 快速定位资产

---

# 二、文件分工

## 1. artifacts.db

详细记录所有产物。

路径：

```text
workspace/projects/{project_id}/artifacts.db
workspace/books/{book_id}/chapters/{chapter_id}/artifacts.db
```

记录内容包括：

- JSON 文件
- 图片
- 音频
- 视频
- 字幕
- 封面
- 中间结果
- 模块调试结果

## 2. manifest.json

只保留轻量摘要和关键输出。

示例：

```json
{
  "artifact_store": "artifacts.db",
  "artifact_summary": {
    "total": 0,
    "by_module": {},
    "by_type": {}
  },
  "key_outputs": {
    "01_novel_parser": {
      "novel_analysis": {
        "type": "json",
        "path": "01_novel_parser/novel_analysis.json"
      }
    }
  }
}
```

---

# 三、关键输出与普通产物

## 关键输出

关键输出是后续模块最常用、必须快速定位的文件。

例如：

```text
01_novel_parser/novel_analysis.json
01_novel_parser/events.json
02_script_writer/script.json
03_character_library/characters.json
04_scene_library/scenes.json
05_prop_library/props.json
06_storyboard/storyboard.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
09_video/video_manifest.json
10_final_assembly/final.mp4
```

关键输出需要同时写入：

```text
artifacts.db
manifest.json 的 key_outputs
```

## 普通批量产物

普通批量产物数量可能很多。

例如：

```text
shot_001.png
shot_002.png
clip_001.mp4
clip_002.mp4
```

这些只需要写入：

```text
artifacts.db
```

不要全部塞进 `manifest.json`。

---

# 四、后续模块查找上一步资产的规则

后续模块查找资产时，遵守以下顺序：

```text
第一优先级：manifest.json 的 key_outputs
第二优先级：artifacts.db 按 module + name + type 查询
第三优先级：约定目录兜底扫描
```

## 示例 1：02 剧本系统查 01 小说解析结果

优先查：

```text
manifest.key_outputs["01_novel_parser"]["novel_analysis"]
manifest.key_outputs["01_novel_parser"]["events"]
manifest.key_outputs["01_novel_parser"]["conflict_map"]
```

找不到再查数据库：

```text
module = "01_novel_parser"
type = "json"
name = "novel_analysis"
```

## 示例 2：06 分镜系统查资产库

长篇项目优先查共享资产库：

```text
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/props/props.json
```

短篇项目查当前项目关键输出：

```text
manifest.key_outputs["03_character_library"]["characters"]
manifest.key_outputs["04_scene_library"]["scenes"]
manifest.key_outputs["05_prop_library"]["props"]
```

## 示例 3：09 视频系统查分镜图

优先查：

```text
manifest.key_outputs["07_storyboard_image"]["image_manifest"]
```

再从数据库查全部图片：

```text
module = "07_storyboard_image"
type = "image"
```

---

# 五、推荐产物命名

为了让后续模块容易查找，关键输出名称必须固定。

```text
01_novel_parser:
  novel_analysis
  events
  raw_characters
  raw_scenes
  raw_props
  conflict_map
  emotion_curve
  module_handoff

02_script_writer:
  script
  script_text
  script_meta

03_character_library:
  characters
  character_alias_map

04_scene_library:
  scenes
  scene_alias_map

05_prop_library:
  props
  prop_alias_map

06_storyboard:
  storyboard
  storyboard_csv
  storyboard_meta

07_storyboard_image:
  image_manifest
  storyboard_image

08_audio:
  audio_script
  final_audio
  audio_manifest

09_video:
  video_manifest
  video_clip

10_final_assembly:
  final_video
  cover
  subtitles
  final_manifest
```

---

# 六、数据库不是代替目录

数据库只负责索引。

真实文件仍然保存在项目目录里：

```text
workspace/projects/{project_id}/{module_name}/
workspace/books/{book_id}/chapters/{chapter_id}/{module_name}/
workspace/books/{book_id}/shared_assets/
```

删除项目目录时，文件和 `artifacts.db` 一起删除。

---

# 七、最高原则

```text
manifest.json = 给人和 Codex 快速看关键输出
artifacts.db = 给程序查全部产物
目录结构 = 保存真实文件
```

不要让 manifest.json 变成巨型数据库。

不要让后续模块靠猜目录找文件。
