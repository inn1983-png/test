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
02 剧本改编系统已升级到 schema 1.2，成为音频驱动、单帧分镜友好、外观/换装状态可追踪、多版本评估、失败样本回灌的真实 LLM 子系统。
03/04/05 已从旧 scaffold library 目录切换为真实资产 system：03_character_system、04_scene_system、05_prop_system。
03/04/05 已升级为五阶段真实资产系统：A 合并、B 资产卡、C 剧本绑定、D 模块总检、E 面向 06 的资产复核。
06_storyboard 已升级为五阶段真实 LLM 单帧分镜系统：A 资产闸门、B 分镜规划、C 单帧分镜、D 连续性绑定、E 总检。
01/02/03/04/05/06 已统一接入本地 Gemma JSON 输出护栏，适配 Gemma 4 31B Q4 等本地量化模型。
01/02/03/04/05/06 的 parse_json_from_text 与 repair fallback 已统一清理 analysis / reasoning / chain_of_thought / _local_model_output_contract 等内部字段。
00 validate_pipeline.py 已修正为识别 run_staged.py，并使用新的 03/04/05 system 模块顺序。
00 resource_manager.py 已改成阶段感知资源释放：01–06 LLM 常驻，06→07 才释放 LLM。
configs/local_resource_release.json 已从旧 library 模块名切换为 system 模块名，并新增 phase_commands。
04_scene_system 已修正 parent_scene 校验：只有 sub_scene 必须非空绑定 parent_scene，main/temporary/background 可为空但字段需存在。
05_prop_system 已修正 05B prop_type 枚举，与 asset_level 统一为 key_prop/action_prop/background_object/mentioned_only。
```

---

# 当前 pipeline 顺序

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

关键产物：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
03_character_system/characters.json
04_scene_system/scenes.json
05_prop_system/props.json
06_storyboard/storyboard.json
07_storyboard_image/image_manifest.json
08_audio/final_audio.wav
09_video/video_manifest.json
10_final_assembly/final.mp4
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

---

# 本地模型资源释放规则

```text
01–06：LLM_TEXT_PHASE，Gemma/本地 LLM 常驻，不在每个模块结束后主动卸载。
06 → 07：进入图片阶段前 release_llm_resources，释放 LLM 显存。
07：图片生成 / ComfyUI 阶段，完成后按需 release_image_resources。
08：TTS / CosyVoice2 阶段，按显存情况 release_audio_resources。
09：视频模型 LTX2.3 阶段，加载前释放其他大模型，完成后 release_video_resources。
10：普通合成阶段，不默认加载大模型。
```

01–06 模块即使在 finally 调用 `resource_manager.release_local_resources(MODULE_NAME)`，也只做轻量清理，不主动卸载 LLM。

---

# 角色一致性最新定案：定妆照 → 造型照 → 分镜图

为保证角色一致性与换装稳定，采用以下链路：

```text
02 记录 appearance_state_changes，明确默认外观、换装、伪装、衣服破损、穿戴物新增/摘除/强调等剧情状态变化。
03 建立角色稳定身份、定妆照需求、costume_variants，并直接读取 02 appearance_state_changes。
05 只管理可独立强调的穿戴物/关键道具，并用 wearable_policy 标明是否并入造型。
06 输出 character_lock_reference 与 appearance_asset_requirements，并直接读取 02 appearance_state_changes，只定义引用关系，不生成图片。
07 后续先生成/引用角色定妆照锁脸，再基于定妆照图生图换衣服、加常驻穿戴物，生成角色造型照，最后正式分镜图引用角色造型照。
```

核心原则：

```text
先锁脸，再换装。
服装主体归 03 costume_variants，不把同一角色的不同衣服拆成不同角色。
腰牌、面具、玉佩、凤冠、面纱、特殊披风、官帽、护腕等可独立强调的穿戴物归 05。
02 负责记录换装事件和外观状态变化，不负责生成资产。
03 负责把外观状态变化转成 costume_variants，不生成图片。
06 每帧引用 canonical_name + character_lock_reference + costume_id + appearance_asset_key + wearable_props。
07 暂未实现，后续新开对话单独做。
```

---

# 01 小说解析系统

正式入口：

```text
01_novel_parser/run_staged.py
```

最高规则：

```text
只要文章里提到过的人、地点、物件，都必须作为候选输出。
重要性只作为 importance 字段评分，不能作为是否提取的门槛。
候选过多不算错误；遗漏才需要返工。
01 不负责最终筛选、合并、去重。03/04/05 负责标准化、资产分级和复核。
```

01 禁止做：

```text
改写小说
扩写剧情
压缩成剧本
生成正式剧本
生成分镜
生成图像提示词
生成视频提示词
直接写入 shared_assets
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
02 输出 visual_dramatic_units / storyboard_hints / continuity_chain 等剧本层动作链和连续性提示。
02 还必须输出 appearance_state_changes，用于 03 生成 costume_variants、用于 06 选择 costume_id / appearance_asset_key。
```

02E 必须输出：

```text
appearance_state_changes：记录 default_appearance / costume_change / disguise / damage_state / wearable_added / wearable_removed / wearable_emphasized。
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

03B 每个 main/supporting 角色必须输出：

```text
canonical_name
appearance
costume
default_costume_id
costume_variants
needs_fixed_face
reference_image_plan
source_evidence
usage_in_script
```

03 新增硬规则：

```text
main/supporting 必须包含 default_costume_id / costume_variants。
default_costume_id 必须存在于 costume_variants。
costume_variants 必须且只能有一个 is_default=true。
换装不能拆成新角色。
03 必须参考 02 appearance_state_changes 生成服装版本。
03 不生成图片，只写定妆照和服装版本需求。
```

03E 复核必须检查：

```text
是否漏掉主角/反派/关键配角
是否把同一角色拆成多个
是否按年龄段/称谓/职务拆角色
asset_level / fixed face / reference plan 是否合理
main/supporting 是否缺 default_costume_id / costume_variants
02 出现换装、伪装、婚服、夜行服、破损衣服、孝服等阶段时是否有对应 costume_variant
06 是否能直接引用 canonical_name + costume_id
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
parent_scene：字段必须存在；只有 sub_scene 必须非空绑定 parent_scene，main_scene/temporary/background 可为空但字段需存在
reference_image_plan
```

04 不生成图片，只写参考图计划。场景优先全景图，不要一开始做大量多角度。

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

05B 每个道具必须输出：

```text
canonical_prop_name
prop_type
wearable_type
wearable_policy
bound_character_names
bound_costume_ids
asset_level
needs_reference_image
reference_image_plan
source_evidence
usage_in_script
```

wearable_policy 枚举：

```text
not_wearable
merge_into_appearance_asset
independent_prop_reference
both
```

05 规则：

```text
官服、常服、夜行衣、婚服、孝服、破损衣服等完整服装版本归 03 costume_variants。
腰牌、面具、玉佩、凤冠、面纱、特殊披风、官帽、护腕等可独立强调的穿戴物归 05。
merge_into_appearance_asset 表示后续 07 可在角色造型照阶段融合。
independent_prop_reference 表示正式分镜图阶段仍可独立引用。
05 不生成图片，只写参考图计划。
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
只能输出 character_lock_reference / appearance_asset_requirements / appearance_asset_key / reference_requirements / composition_notes / continuity_notes。
每帧角色必须引用 03 canonical_name。
每帧角色服装必须引用 03 costume_id。
每帧场景必须引用 04 canonical_scene_name。
每帧道具必须引用 05 canonical_prop_name。
必须参考 02 appearance_state_changes 选择 costume_id / appearance_asset_key。
不允许新增不存在于资产库的主角色、服装版本、主场景、关键道具。
如发现资产缺失，写入 upstream_blocking_issues，建议 03/04/05 对应阶段重跑。
```

06C 必须输出：

```text
appearance_asset_requirements：07 未来生成角色造型照的需求索引。
frames[].characters[].character_lock_reference：定妆照锁脸引用。
frames[].characters[].costume_id：角色服装版本。
frames[].characters[].appearance_asset_key：造型照引用索引。
frames[].characters[].wearable_props：并入造型照的常驻穿戴物。
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
02 最终 schema_validator.py 会检查 appearance_state_changes 是否存在、是否引用真实 segment_id / voice_line_id / visual_unit_id。
03 最终 schema_validator.py 会检查角色去重、主/配角 fixed face、default_costume_id、costume_variants、默认服装唯一性。
04 最终 schema_validator.py 会检查场景层级、parent_scene、主场景参考图计划。
05 最终 schema_validator.py 会检查道具分级、wearable_type、wearable_policy、bound_character_names、bound_costume_ids、禁止图像提示词字段。
06 最终 schema_validator.py 会检查 frames、sequence_index 连续性、稳定资产名引用、costume_id 引用、appearance_asset_key 定义、allowed_asset_names 与 03/04/05 一致性、禁止图像提示词字段、资产不可用时必须有 upstream_blocking_issues。
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

---

# 用户最新明确要求

```text
03/04/05 形成稳定资产库，让 06 单帧分镜可以直接引用稳定角色名、稳定场景名、稳定道具名，避免角色串脸、场景漂移、道具混乱。
不同阶段角色可能有不同衣服，服装主体要归入 03 costume_variants，不要把换装拆成新角色。
为了保证角色一致性，后续 07 应先生成角色定妆照锁脸，再用定妆照图生图换衣服加道具，生成角色造型照，再被正式分镜图引用。
05 只处理可独立强调或可并入造型的穿戴物，不主管完整服装版本。
02 必须记录 appearance_state_changes，给 03/06 提供换装和穿戴状态依据，不能让 03/06 靠猜。
06 只生成单帧分镜 JSON，不生成图片、不调用 ComfyUI、不生成最终视频。
06 必须严格引用 03/04/05 稳定资产名和 03 costume_id，不允许新增不存在于资产库的主角色、服装版本、主场景、关键道具。
06 如发现资产缺失，不能自己硬补，要输出 upstream_blocking_issues，建议 03/04/05 对应阶段重跑。
06 为 07 图片生成服务，但不能直接写图像提示词；只能输出 character_lock_reference / appearance_asset_requirements / reference_requirements / composition_notes / continuity_notes。
07 暂不改，等 01–06 全部完成后新开对话单独处理。
用户准备使用本地 Gemma 4 31B Q4，所以 01/02/03/04/05/06 需要强 JSON 护栏、低温度默认值、输出控制字段清理。
00–06 都属于 LLM 文本阶段，不应每个模块结束就释放 LLM；06→07 才释放 LLM 显存。
```
