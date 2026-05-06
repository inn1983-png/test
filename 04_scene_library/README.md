# 04 场景库系统

## 模块定位

场景库系统负责管理单项目或全书共享的场景资产。

它的目标是保证场景稳定，避免同一个地点在不同章节、不同分镜中反复变化。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/01_novel_parser/raw_scenes.json
workspace/projects/{project_id}/01_novel_parser/events.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/new_scene_candidates.json
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/scenes/scene_alias_map.json
```

---

## 输出

短篇 / 单章项目：

```text
workspace/projects/{project_id}/04_scene_library/scenes.json
workspace/projects/{project_id}/04_scene_library/scene_alias_map.json
```

长篇小说项目：

```text
workspace/books/{book_id}/shared_assets/scenes/scenes.json
workspace/books/{book_id}/shared_assets/scenes/scene_alias_map.json
workspace/books/{book_id}/shared_assets/scenes/images/
```

---

## 核心任务

1. 合并同一场景的不同叫法
2. 建立稳定场景 ID
3. 记录地点、时代、时间、环境、氛围、光照
4. 生成可用于生图的场景描述
5. 管理场景参考图
6. 长篇项目中维护全书共享场景库

---

## 最高规则

场景库负责稳定场景，不负责改写剧情。

例如：

```text
汴京西街
西街
街道
炊饼摊所在街道
```

如果原文语境显示它们是同一地点，应合并为一个稳定场景。

---

## 禁止事项

- 不生成剧本
- 不生成分镜
- 不生成视频
- 不凭空新增原文没有的场景
- 不随意把古代场景改成现代场景

---

## 与其他模块关系

```text
01_novel_parser → 04_scene_library → 06_storyboard / 07_storyboard_image
```
