# 05 道具库系统

## 模块定位

05_prop_system 只负责道具资产标准化。

它读取：

```text
01_novel_parser/novel_analysis.json
02_script_writer/script.json
```

重点使用：

```text
01: candidate_props / paragraphs / events / asset_binding_hints
02: segments / visual_dramatic_units / storyboard_hints / scene_beats / continuity_chain
```

输出：

```text
05_prop_system/props.json
05_prop_system/prop_meta.json
```

## 绝对边界

05 只做：

```text
道具合并
道具别名归并
关键道具/普通道具/背景物件区分
稳定道具卡
剧本使用绑定
证据链
道具连续性规则
道具库质量评分
```

05 禁止做：

```text
生成图片
生成分镜
生成图像提示词
生成视频提示词
ComfyUI 调用
角色资产标准化
场景资产标准化
```

## 分阶段真实 LLM 流程

正式入口：

```bash
python 05_prop_system/run_staged.py
```

阶段：

```text
05A prop_merge_plan：合并同一道具的不同说法
05B prop_cards：输出稳定道具卡
05C script_usage_binding：绑定 02 剧本里的道具使用
05D quality_check：总检评分，可触发连锁重跑
```

## 评分与重跑

每个阶段生成后都会进入 `quality_checker.py` 评分。

低于阈值时会生成 `revision_instructions`，并把修改意见传回同阶段 LLM 自动重跑。

05D 如果输出：

```json
{
  "quality_report": {
    "needs_retry": true,
    "retry_stages": ["05A"]
  }
}
```

系统会从最早问题阶段开始连锁重跑：

```text
05A → 05B → 05C → 05D
```

## JSON 修复机制

LLM 返回 JSON 解析失败时，`json_repair.py` 会把 broken_json 和错误原因发回 LLM，只修复 JSON 格式，不新增业务内容。

## 最终硬规则校验

`schema_validator.py` 会检查：

```text
props 是否为空
prop_id 是否重复
canonical_prop_name 是否重复
aliases 是否互相冲突
是否出现 prompt / image_prompt / desc_prompt 等越界字段
source_evidence 是否存在
usage_in_script 是否为数组
```

## 核心输出字段

每个道具必须包含：

```text
canonical_prop_name
aliases
prop_type
owner_character
usage_function
appearance
material
risk_notes
source_evidence
usage_in_script
```

## 最高规则

```text
合并同一道具的不同说法。
区分关键道具、普通道具、背景物件。
道具描述要适合后续 06 单帧分镜引用，但不要写图像提示词。
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
