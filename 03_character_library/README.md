# 03 角色库系统

## 模块定位

角色库系统负责管理全书或单项目的角色资产。

它不是剧本系统，也不是分镜系统。

它的核心任务是保证角色稳定、不串脸、不重复、不按年龄乱拆。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/01_novel_parser/raw_characters.json
workspace/projects/{project_id}/01_novel_parser/events.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/new_character_candidates.json
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/characters/character_alias_map.json
```

---

## 输出

短篇 / 单章项目：

```text
workspace/projects/{project_id}/03_character_library/characters.json
workspace/projects/{project_id}/03_character_library/character_alias_map.json
```

长篇小说项目：

```text
workspace/books/{book_id}/shared_assets/characters/characters.json
workspace/books/{book_id}/shared_assets/characters/character_alias_map.json
workspace/books/{book_id}/shared_assets/characters/images/
```

---

## 核心任务

1. 合并同一角色的不同称呼
2. 建立稳定角色 ID
3. 记录角色性别、身份、关系、外貌、性格
4. 记录证据来源
5. 生成可用于图像系统的角色描述
6. 管理角色参考图
7. 长篇项目中维护全书共享角色库

---

## 最高规则

同一角色只允许有一个稳定 ID。

严禁把同一人物拆成：

```text
年轻张捕头
中年张捕头
老年张捕头
张捕头
张头
捕头
```

应该合并为同一角色。

---

## 禁止事项

- 不写剧本
- 不生成分镜
- 不生成视频
- 不随意新增原文没有的人物
- 不覆盖已有角色图，除非明确执行资产更新任务

---

## 与其他模块关系

```text
01_novel_parser → 03_character_library → 06_storyboard / 07_storyboard_image
```
