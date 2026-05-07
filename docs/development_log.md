# 开发记录与协作规则

本文档只记录关键架构、重要规则、schema 变化和用户明确要求。重复流水账、过细命令、已被 README 覆盖的长篇说明可以删除。

---

# 协作规则

1. 用户给出明确方向后，可以连续修改代码和文档，不需要每个小改动都反复确认。
2. 每轮重要改动后，必须同步更新 README 或 docs。
3. 每轮结束必须总结：做了什么、改了哪些文件、下一步建议。
4. 需要提前确认的情况：删除大量文件、重构核心架构、改变模块边界、修改既定数据目录规则、可能破坏现有可运行流程。

---

# 当前阶段

```text
00 + 01–10 子系统框架已能闭环。
01 小说解析系统已具备真实 LLM 分阶段解析、评分、JSON 修复、总检重跑和 schema 硬校验。
02 剧本改编系统已升级到 schema 1.2，成为音频驱动、单帧分镜友好、多版本评估、失败样本回灌的真实 LLM 子系统。
03/04/05 已从旧 scaffold library 目录切换为真实资产 system：03_character_system、04_scene_system、05_prop_system。
03/04/05 已加入资产分级与参考图策略：01 提取一切，03/04/05 先合并再分级，06 只引用稳定主资产。
```

---

# 关键架构

## 00 总控

模块运行入口规则：

```text
如果模块目录存在 run_staged.py，00 优先运行 run_staged.py。
否则运行 run.py。
```

当前 pipeline 模块顺序：

```text
01_novel_parser
02_script_writer
03_character_system
04_scene_system
05_prop_system
06_storyboard
07_storyboard_image
08_audio
09_video
10_final_assembly
```

旧 scaffold 目录已移除：

```text
03_character_library
04_scene_library
05_prop_library
```

---

# 01 小说解析系统

正式入口：

```text
01_novel_parser/run_staged.py
```

候选提取最高规则：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
重要性只作为 importance 字段评分，不能作为是否提取的门槛。
候选过多不算错误；遗漏才需要返工。
01 不负责最终筛选、合并、去重。03/04/05 负责标准化与资产分级。
```

---

# 02 剧本改编系统

正式入口：

```text
02_script_writer/run_staged.py
```

02 单帧分镜路线：

```text
单帧 = 生产单位
四宫格 = 后续连续性预览 / 检查单位
02 只输出 visual_dramatic_units / storyboard_hints / continuity_chain 等剧本层动作链和连续性提示。
```

02 禁止做：

```text
角色资产标准化
场景资产标准化
道具资产标准化
正式分镜生成
图像提示词生成
视频提示词生成
ComfyUI 调用
直接写入 shared_assets
```

---

# 03 角色库系统

正式入口：

```text
03_character_system/run_staged.py
```

阶段：

```text
03A alias_merge_plan
03B character_cards
03C script_usage_binding
03D quality_check
```

03 最高规则：

```text
合并同一角色的不同称呼。
禁止按年龄段拆角色。
禁止把身份称谓、昵称、职务称谓拆成新角色。
角色描述必须稳定、清晰、不可互相污染，服务 06 单帧分镜引用稳定角色名。
```

03 资产分级：

```text
asset_level = main / supporting / extra_group / mentioned_only
needs_fixed_face = true / false
reference_image_priority = required / optional / not_needed
reference_image_plan 必须给出推荐参考图策略
```

03 参考图策略：

```text
main：front_face_half_body + full_body_front
supporting：front_face_half_body
extra_group / mentioned_only：不强制参考图
```

03 图像资产最高规则：

```text
先单视图稳定，不要一开始做三视图。
不要把正面/侧面/背面拼成一张三视图图板。
如后续确实需要三视图，必须拆成 front / side / back 多张独立图。
```

03 schema 硬校验新增：

```text
asset_level 合法性
主/配角 needs_fixed_face=true
龙套/仅提及角色不强制 required 参考图
核心角色 reference_image_plan 必须包含 front_face_half_body
```

---

# 04 场景库系统

正式入口：

```text
04_scene_system/run_staged.py
```

阶段：

```text
04A scene_merge_plan
04B scene_cards
04C script_usage_binding
04D quality_check
```

04 最高规则：

```text
合并同一场景的不同说法。
区分主场景、子场景、临时地点。
场景描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
```

04 资产分级：

```text
asset_level = main_scene / sub_scene / temporary / background
needs_reference_image = true / false
parent_scene
reference_image_plan
```

04 参考图策略：

```text
main_scene：wide_establishing_view，先用全景图稳定空间
sub_scene：需要时再补 local_area_view
temporary / background：只保留文字资产，不强制做图
```

04 图像资产最高规则：

```text
场景优先全景图，不要一开始做大量多角度。
先主场景全景，再根据 06/07 失败情况补子区域局部图。
```

04 schema 硬校验新增：

```text
asset_level 合法性
主场景 needs_reference_image=true
主场景 reference_image_plan 必须包含 wide_establishing_view
子场景必须绑定 parent_scene
禁止出现 prompt / image_prompt / desc_prompt 等越界字段
```

---

# 05 道具库系统

正式入口：

```text
05_prop_system/run_staged.py
```

阶段：

```text
05A prop_merge_plan
05B prop_cards
05C script_usage_binding
05D quality_check
```

05 最高规则：

```text
合并同一道具的不同说法。
区分关键道具、动作道具、背景物件、仅提及物件。
道具描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
```

05 资产分级：

```text
asset_level = key_prop / action_prop / background_object / mentioned_only
needs_reference_image = true / false
reference_image_plan
```

05 参考图策略：

```text
key_prop：clean_front_view；复杂道具可加 side_view
action_prop：需要时再做 clean_front_view
background_object / mentioned_only：不强制做图，尽量归入场景元素
```

05 图像资产最高规则：

```text
关键道具用单独干净图。
普通道具和背景物件不要全部做图，否则资产库会爆炸。
道具图不要和角色/场景混在一起。
```

05 schema 硬校验新增：

```text
asset_level 合法性
关键道具 needs_reference_image=true
关键道具 reference_image_plan 必须包含 clean_front_view
背景/仅提及道具不强制参考图
禁止出现 prompt / image_prompt / desc_prompt 等越界字段
```

---

# 03/04/05 共同真实执行机制

## 真实 LLM

03/04/05 不支持正式流程使用 scaffold 占位结果。必须配置：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

可选：

```bash
set AI_DRAMA_LLM_API_KEY=你的 key
set AI_DRAMA_LLM_TIMEOUT_SEC=180
set AI_DRAMA_LLM_TEMPERATURE=0.2
```

## 阶段评分与修改意见重跑

```text
每阶段生成后 quality_checker.py 评分。
低于阈值时生成 revision_instructions，并把修改意见传回同阶段 LLM 自动重跑。
```

## 总检连锁重跑

```text
03D / 04D / 05D 输出 needs_retry=true 和 retry_stages 时，stage_runner.py 会从最早问题阶段开始，连同后续阶段再跑一轮。
```

## JSON 修复机制

```text
LLM 返回 JSON 解析失败时，json_repair.py 会把 broken_json 和错误原因发回 LLM。
该机制只修复 JSON 格式，不新增业务内容。
```

---

# 下一步建议测试顺序

准备：

```text
workspace/projects/project_test_001/input/novel.txt
```

配置本地 LLM：

```bash
set AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions
set AI_DRAMA_LLM_MODEL=你的本地模型名
```

建议依次测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 03_character_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 04_scene_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 05_prop_system
```

完整测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

---

# 用户最新明确要求

```text
01 负责提取一切。
03/04/05 不要简单删除候选，而是合并、分级、输出稳定资产库。
03/04/05 形成稳定资产库，让 06 单帧分镜可以直接引用稳定角色名、稳定场景名、稳定道具名，避免角色串脸、场景漂移、道具混乱。
角色资产先单视图稳定，不要一开始做三视图；三视图如需要必须拆成多张独立图。
场景资产主场景优先全景图，子场景后续按需补局部图，不要一开始做大量多角度。
道具资产关键道具单独干净图，背景物件尽量归入场景，不要全部做图。
```
