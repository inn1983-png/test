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
01 小说解析系统已修正为真实 LLM 分阶段入口 run_llm_stages，不再调用旧 scaffold。
02 剧本改编系统已升级到 schema 1.2，成为音频驱动、单帧分镜友好、多版本评估、失败样本回灌的真实 LLM 子系统。
03/04/05 已从旧 scaffold library 目录切换为真实资产 system：03_character_system、04_scene_system、05_prop_system。
03/04/05 已升级为五阶段真实资产系统：A 合并、B 资产卡、C 剧本绑定、D 模块总检、E 面向 06 的资产复核。
06_storyboard 已升级为五阶段真实 LLM 单帧分镜系统：A 资产闸门、B 分镜规划、C 单帧分镜、D 连续性绑定、E 总检。
01/02/03/04/05/06 已移除 write_placeholder_output，不再生成占位 result.json。
01/02/03/04/05/06 已统一接入本地 Gemma JSON 输出护栏，适配 Gemma 4 31B Q4 等本地量化模型。
01/02/03/04/05/06 的 parse_json_from_text 与 repair fallback 已统一清理 analysis / reasoning / chain_of_thought / _local_model_output_contract 等内部字段。
00 validate_pipeline.py 已修正为识别 run_staged.py，并使用新的 03/04/05 system 模块顺序。
00 resource_manager.py 已改成阶段感知资源释放：01–06 LLM 常驻，06→07 才释放 LLM。
configs/local_resource_release.json 已从旧 library 模块名切换为 system 模块名，并新增 phase_commands。
04_scene_system 已修正 parent_scene 校验：只有 sub_scene 必须非空绑定 parent_scene，main/temporary/background 可为空但字段需存在。
05_prop_system 已修正 05B prop_type 枚举，与 asset_level 统一为 key_prop/action_prop/background_object/mentioned_only。
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

00 当前关键修正：

```text
validate_pipeline.py 不再只检查 run.py，也会接受 run_staged.py。
DEFAULT_MODULE_ORDER 已从旧 03_character_library / 04_scene_library / 05_prop_library 改为 03_character_system / 04_scene_system / 05_prop_system。
validate_pipeline.py 会拦截旧 library 模块，避免重新混入 pipeline。
run_pipeline.py 依赖检查通过 manifest key_outputs、artifacts.db、run_dir/module/file fallback 三路解析上游产物。
run_pipeline.py 会在模型阶段边界调用 resource_manager 的专用释放函数。
```

旧 scaffold 目录已移除：

```text
03_character_library
04_scene_library
05_prop_library
```

---

# 本地 Gemma 4 31B Q4 适配规则

统一文件：

```text
00_common/llm_prompt_guard.py
```

01/02/03/04/05/06 的 LLMClient.complete_json 都会自动套用：

```text
只输出一个 JSON object
禁止 Markdown / ```json / 前言 / 后记
必须使用 JSON null/true/false
必填字段不能省略
顶层必须是 object，不能是 array
输出前自检能被 json.loads 解析
```

输出清理硬规则：

```text
parse_json_from_text 在 json.loads 后必须调用 remove_internal_output_fields(value)。
complete_json 的 repair_callback 返回后也必须再次调用 remove_internal_output_fields(value)。
清理字段包括：_local_model_output_contract、analysis、reasoning、chain_of_thought、scratchpad、thoughts、thinking、internal_reasoning、internal_notes、debug、debug_notes，以及 _local_model_ 前缀字段。
清理是递归的，防止本地模型把控制字段复制到嵌套业务 JSON。
```

默认 temperature：

```text
01：0.1
02：0.15
03/04/05/06：0.1
```

如果需要统一覆盖，可以设置：

```bash
set AI_DRAMA_LLM_TEMPERATURE=0.1
```

---

# 本地模型资源释放规则

统一文件：

```text
00_common/resource_manager.py
configs/local_resource_release.json
```

阶段规则：

```text
01–06：LLM_TEXT_PHASE，Gemma/本地 LLM 常驻，不在每个模块结束后主动卸载。
06 → 07：进入图片阶段前 release_llm_resources，释放 LLM 显存。
07：图片生成 / ComfyUI 阶段，完成后按需 release_image_resources。
08：TTS / CosyVoice2 阶段，按显存情况 release_audio_resources。
09：视频模型 LTX2.3 阶段，加载前释放其他大模型，完成后 release_video_resources。
10：普通合成阶段，不默认加载大模型。
```

模块仍然可以在 finally 中调用：

```python
resource_manager.release_local_resources(MODULE_NAME)
```

但 01–06 的该调用只做轻量清理：

```text
gc.collect()
不主动 torch.cuda.empty_cache()
不执行外部卸载命令
不卸载 LLM / Gemma
```

阶段边界释放由 00_main_controller/run_pipeline.py 统一处理：

```text
06_storyboard -> 07_storyboard_image：release_llm_resources()
07_storyboard_image -> 08_audio：release_image_resources()
08_audio -> 09_video：release_audio_resources() + release_image_resources()
09_video -> 10_final_assembly：release_video_resources()
```

---

# 01 小说解析系统

正式入口：

```text
01_novel_parser/run_staged.py
```

当前修正：

```text
run_staged.py 已从旧 run_scaffold_stages 改为 run_llm_stages。
已移除 write_placeholder_output。
新增 novel_meta.json 真实元信息输出。
LLM 输出已接入 JSON guard + 内部控制字段递归清理。
```

候选提取最高规则：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
重要性只作为 importance 字段评分，不能作为是否提取的门槛。
候选过多不算错误；遗漏才需要返工。
01 不负责最终筛选、合并、去重。03/04/05 负责标准化、资产分级和复核。
```

---

# 02 剧本改编系统

正式入口：

```text
02_script_writer/run_staged.py
```

当前修正：

```text
已移除 write_placeholder_output。
script.json 顶层已补回 event_coverage_map，修复 schema_validator 检查事件覆盖但 merge_stage_outputs 未输出的问题。
LLM 输出已接入 JSON guard + 内部控制字段递归清理。
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
03E asset_review
```

03 资产分级：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis 必须引用 01 story_understanding / story_spine / events / conflicts / high_retention_segments / character_arc_map / paragraphs
asset_level = main / supporting / extra_group / mentioned_only
needs_fixed_face = true / false
reference_image_priority = required / optional / not_needed
reference_image_plan
```

03E 复核：

```text
面向 06 单帧分镜复核，不是单纯格式检查。
必须检查遗漏、误合并、误拆分、误分级、过度资产化、固定脸策略、参考图计划和 06 可用性。
如果 01 candidate_characters 也遗漏但 01 理解中明确存在，写入 upstream_blocking_issues，建议 01D 重跑。
如果 03 内部不通过，输出 retry_stages 和 revision_instructions，从最早问题阶段连锁重跑。
```

03 图像资产最高规则：

```text
03 不生成图片，只写参考图计划。
先单视图稳定，不要一开始做三视图。
不要把正面/侧面/背面拼成一张三视图图板。
图片由 07 根据 06 实际分镜需求统一生成。
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
04E asset_review
```

04 资产分级：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis 必须引用 01 story_understanding / story_spine / events / conflicts / high_retention_segments / scene_value_map / visual_risk_report / paragraphs
asset_level = main_scene / sub_scene / temporary / background
needs_reference_image = true / false
parent_scene：字段必须存在；只有 sub_scene 必须非空绑定主场景，main_scene/temporary/background 可为空但字段需存在
reference_image_plan
```

04E 复核：

```text
面向 06 单帧分镜复核。
必须检查场景拆太碎、错误合并、主/子/临时分级、parent_scene、全景图计划、临时地点误升主场景、背景物件误作场景和 06 可用性。
如果 01 candidate_scenes 也遗漏但 01 理解中明确存在，写入 upstream_blocking_issues，建议 01D 重跑。
如果 04 内部不通过，输出 retry_stages 和 revision_instructions，从最早问题阶段连锁重跑。
```

04 图像资产最高规则：

```text
04 不生成图片，只写参考图计划。
场景优先全景图，不要一开始做大量多角度。
图片由 07 根据 06 实际分镜需求统一生成。
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
05E asset_review
```

05 资产分级：

```text
asset_importance_score = 0-100
importance_reason
source_understanding_basis 必须引用 01 story_understanding / story_spine / events / conflicts / high_retention_segments / asset_binding_hints / visual_risk_report / paragraphs
asset_level = key_prop / action_prop / background_object / mentioned_only
prop_type 与 asset_level 使用同一组枚举：key_prop / action_prop / background_object / mentioned_only
needs_reference_image = true / false
reference_image_plan
```

05E 复核：

```text
面向 06 单帧分镜复核。
必须检查关键道具遗漏、背景物件误升关键道具、同一道具拆分、普通道具过度资产化、背景物件归入场景元素、owner_character 和 06 可用性。
如果 01 candidate_props 也遗漏但 01 理解中明确存在，写入 upstream_blocking_issues，建议 01D 重跑。
如果 05 内部不通过，输出 retry_stages 和 revision_instructions，从最早问题阶段连锁重跑。
```

05 图像资产最高规则：

```text
05 不生成图片，只写参考图计划。
关键道具用单独干净图。
普通道具和背景物件不要全部做图，否则资产库会爆炸。
图片由 07 根据 06 实际分镜需求统一生成。
```

---

# 06 单帧分镜系统

正式入口：

```text
06_storyboard/run_staged.py
```

阶段：

```text
06A asset_gate
06B storyboard_plan
06C single_frame_storyboard
06D continuity_binding
06E quality_check
```

06 输入：

```text
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
```

06 输出：

```text
06_storyboard/storyboard.json
06_storyboard/storyboard_meta.json
```

06 核心规则：

```text
只生成单帧分镜 JSON。
不生成图片、不调用 ComfyUI、不生成最终视频。
不得输出 prompt / image_prompt / desc_prompt / desc_promopt / negative_prompt / video_prompt / comfyui_prompt。
只能输出 reference_requirements / composition_notes / continuity_notes。
每帧角色必须引用 03 canonical_name。
每帧场景必须引用 04 canonical_scene_name。
每帧道具必须引用 05 canonical_prop_name。
不允许新增不存在于资产库的主角色、主场景、关键道具。
如发现资产缺失，写入 upstream_blocking_issues，建议 03/04/05 对应阶段重跑。
```

06 四宫格规则：

```text
四宫格只是连续性预览 / 检查单位，不是一次性生成四宫格图。
four_grid_preview_groups 可按 1-4、4-7、7-10 重叠组织。
```

---

# 03/04/05/06 共同真实执行机制

## 阶段评分与修改意见重跑

```text
每阶段生成后 quality_checker.py 评分。
低于阈值时生成 revision_instructions，并把修改意见传回同阶段 LLM 自动重跑。
```

## 总检/复核连锁重跑

```text
03D/03E、04D/04E、05D/05E、06D/06E 输出 needs_retry=true 和 retry_stages 时，stage_runner.py 会从最早问题阶段开始，连同后续阶段再跑一轮。
```

## JSON 修复机制

```text
LLM 返回 JSON 解析失败时，json_repair.py 会把 broken_json 和错误原因发回 LLM。
该机制只修复 JSON 格式，不新增业务内容。
修复后的 JSON 也会再次进入内部控制字段清理。
```

## 最终 schema 硬校验

```text
03/04/05 最终 schema_validator.py 不只查字段，还会检查 asset_importance_score、source_understanding_basis、asset_review_report、downstream_readiness_for_06、main/optional/do_not_reference 清单。
06 最终 schema_validator.py 会检查 frames、sequence_index 连续性、稳定资产名引用、allowed_asset_names 与 03/04/05 一致性、禁止图像提示词字段、资产不可用时必须有 upstream_blocking_issues。
注意：schema_validation 不再作为预校验必填字段，避免校验前必然失败。
03E/04E/05E 的 optional_assets_for_06 和 do_not_reference_as_main_asset 允许为空数组。
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
set AI_DRAMA_LLM_MODEL=你的 Gemma 模型名
set AI_DRAMA_LLM_TEMPERATURE=0.1
set AI_DRAMA_LLM_TIMEOUT_SEC=240
```

先校验 pipeline：

```bash
python 00_main_controller/validate_pipeline.py --pipeline pipeline.json --strict-order
```

建议依次测试：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 01_novel_parser
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 02_script_writer
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 03_character_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 04_scene_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 05_prop_system
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --only-module 06_storyboard
```

完整测试到 06：

```bash
python 00_main_controller/run_pipeline.py --mode project --project-id project_test_001 --from-module 01_novel_parser
```

如果只想验证 00–06，不加载后续模型，可以先逐个跑到 06，或临时用 `--only-module` 分段测试。

---

# 用户最新明确要求

```text
01 负责提取一切。
03/04/05 不要简单删除候选，而是合并、分级、复核、输出稳定资产库。
03/04/05 必须真实可用，方便后续测试，不要用占位文件。
复核必须使用 01 阶段对小说的真正理解来判断遗漏、误合并、误分级、过度资产化。
复核发现遗漏不能直接在 E 阶段硬补，必须通过 retry_stages 触发前置阶段重跑；如果 01 自己也漏提，则写 upstream_blocking_issues。
03/04/05 形成稳定资产库，让 06 单帧分镜可以直接引用稳定角色名、稳定场景名、稳定道具名，避免角色串脸、场景漂移、道具混乱。
03/04/05 不生成图片，只写参考图计划；图片由 07 根据 06 实际分镜需求统一生成。
06 必须读取 02_script_writer/script.json、03_character_system/characters.json、04_scene_system/scenes.json、05_prop_system/props.json。
06 只生成单帧分镜 JSON，不生成图片、不调用 ComfyUI、不生成最终视频。
06 必须严格引用 03/04/05 稳定资产名，不允许新增不存在于资产库的主角色、主场景、关键道具。
06 如发现资产缺失，不能自己硬补，要输出 upstream_blocking_issues，建议 03/04/05 对应阶段重跑。
06 为 07 图片生成服务，但不能直接写图像提示词；只能输出 reference_requirements / composition_notes / continuity_notes。
用户准备使用本地 Gemma 4 31B Q4，所以 01/02/03/04/05/06 需要强 JSON 护栏、低温度默认值、输出控制字段清理。
00–06 都属于 LLM 文本阶段，不应每个模块结束就释放 LLM；06→07 才释放 LLM 显存。
```
