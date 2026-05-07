# 03 角色库系统

## 模块定位

03_character_system 只负责角色资产标准化。

它读取：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
```

重点使用：

```text
01: candidate_characters / paragraphs / events / character_arc_map
02: segments / character_name_usage / visual_dramatic_units / storyboard_hints / continuity_chain
```

输出：

```text
03_character_system/characters.json
03_character_system/character_meta.json
```

## 绝对边界

03 只做：

```text
角色合并
角色别名归并
稳定角色卡
剧本使用绑定
证据链
角色连续性规则
角色库质量评分
```

03 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
ComfyUI 调用
场景资产标准化
道具资产标准化
```

## 分阶段真实 LLM 流程

正式入口：

```bash
python 03_character_system/run_staged.py
```

00 总控会优先调用：

```text
run_staged.py
```

阶段：

```text
03A alias_merge_plan：合并同一角色的不同称呼
03B character_cards：输出稳定角色卡
03C script_usage_binding：绑定 02 剧本里的角色使用
03D quality_check：总检评分，可触发连锁重跑
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成：

```text
revision_instructions
```

并把修改意见传回同阶段 LLM 自动重跑。

03D 如果输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["03A"],
    "revision_instructions": []
  }
}
```

系统会从最早问题阶段开始连锁重跑：

```text
03A → 03B → 03C → 03D
```

## JSON 修复机制

LLM 返回 JSON 解析失败时，`json_repair.py` 会把 broken_json 和错误原因发回 LLM，只修复 JSON 格式，不新增业务内容。

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
characters 是否为空
character_id 是否重复
canonical_name 是否重复
aliases 是否互相冲突
是否按年龄段拆角色
canonical_name / aliases / gender / age_range / identity / appearance / costume / temperament / role_function 是否完整
source_evidence 是否存在
usage_in_script 是否为数组
```

## 核心输出字段

每个角色必须包含：

```text
canonical_name
aliases
gender
age_range
identity
appearance
costume
temperament
role_function
source_evidence
usage_in_script
anti_contamination_notes
```

## 最高规则

```text
同一角色只输出一次。
禁止按年龄段拆角色。
禁止把身份称谓、昵称、职务称谓拆成新角色。
角色描述必须稳定、清晰、不可互相污染，服务 06 单帧分镜引用稳定角色名。
```

## LLM 配置

必须配置：

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
