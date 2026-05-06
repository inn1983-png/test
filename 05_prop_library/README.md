# 05 道具库系统

## 模块定位

道具库系统负责管理单项目或全书共享的道具资产。

它的目标是保证关键道具稳定，避免道具在图像和分镜中反复变形、丢失或现代化。

---

## 输入

短篇 / 单章项目：

```text
workspace/projects/{project_id}/01_novel_parser/raw_props.json
workspace/projects/{project_id}/01_novel_parser/events.json
```

长篇小说项目：

```text
workspace/books/{book_id}/chapters/{chapter_id}/01_novel_parser/new_prop_candidates.json
workspace/books/{book_id}/shared_assets/props/props.json
workspace/books/{book_id}/shared_assets/props/prop_alias_map.json
```

---

## 输出

短篇 / 单章项目：

```text
workspace/projects/{project_id}/05_prop_library/props.json
workspace/projects/{project_id}/05_prop_library/prop_alias_map.json
```

长篇小说项目：

```text
workspace/books/{book_id}/shared_assets/props/props.json
workspace/books/{book_id}/shared_assets/props/prop_alias_map.json
workspace/books/{book_id}/shared_assets/props/images/
```

---

## 核心任务

1. 提取并合并关键道具
2. 建立稳定道具 ID
3. 记录道具类别、外观、用途、所属人物或场景
4. 生成可用于生图的道具描述
5. 管理道具参考图
6. 长篇项目中维护全书共享道具库

---

## 关键道具范围

包括但不限于：

```text
武器
官印
文书
信件
衣物
马车
摊位
灯笼
桌椅
食物
刑具
银票
令牌
```

---

## 禁止事项

- 不写剧本
- 不生成分镜
- 不生成视频
- 不把古代道具改成现代物品
- 不凭空新增关键道具

---

## 与其他模块关系

```text
01_novel_parser → 05_prop_library → 06_storyboard / 07_storyboard_image
```
