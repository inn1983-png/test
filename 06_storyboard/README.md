# 06 分镜系统

## 模块定位

分镜系统负责把剧本拆成可生成、可执行、可对接分镜图系统的分镜表。

它不负责写剧本，不负责生成图片，不负责生成视频。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/02_script_writer/script.json
workspace/projects/{project_id}/03_character_library/characters.json
workspace/projects/{project_id}/04_scene_library/scenes.json
workspace/projects/{project_id}/05_prop_library/props.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/02_script_writer/script.json
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/props/props.json
```

---

## 输出

```text
06_storyboard/storyboard.json
06_storyboard/storyboard.csv
06_storyboard/storyboard_meta.json
```

正式运行时输出到：

```text
workspace/projects/{project_id}/06_storyboard/
```

或：

```text
workspace/books/{book_id}/chapters/{chapter_id}/06_storyboard/
```

---

## 核心任务

1. 根据剧本生成分镜表
2. 每个分镜绑定角色、场景、道具
3. 生成画面描述 `desc_promopt`
4. 保留剧本文本来源 `cap`
5. 控制分镜数量
6. 为分镜图系统提供稳定输入

---

## 关键字段

推荐字段：

```json
{
  "shot_id": "shot_001",
  "order": 1,
  "cap": "必须来自剧本或原文的连续文本片段",
  "theme": "压迫",
  "characters": ["char_001"],
  "scene": "scene_001",
  "props": ["prop_001"],
  "camera": "中景·平视·正面",
  "action": "",
  "emotion": "",
  "desc_promopt": ""
}
```

注意：用户常用字段名是 `desc_promopt`，先保持兼容，不要擅自改成 `desc_prompt`。

---

## 最高规则

- `cap` 必须来自剧本或原文连续片段
- 不允许擅自改写 `cap`
- 角色必须引用角色库
- 场景必须引用场景库
- 道具必须引用道具库
- 不允许分镜系统凭空创造新角色
- 第一个分镜可以只出现背景，不出现人物

---

## 与其他模块关系

```text
02_script_writer + 03/04/05 assets → 06_storyboard → 07_storyboard_image
```
