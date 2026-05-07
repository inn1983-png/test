from __future__ import annotations

from typing import Any

LOCAL_GEMMA_JSON_GUARD = """
# 本地/远程 LLM JSON 输出护栏

你运行在自动化视频流水线环境。为保证 01/02/03/04/05/06 等 LLM_TEXT_PHASE 稳定，必须严格遵守：

1. 只输出一个合法 JSON object。
2. 第一个非空字符必须是 {，最后一个非空字符必须是 }。
3. 不要输出 Markdown，不要输出 ```json，不要输出解释、前言、后记、免责声明。
4. 不要输出注释，不要使用单引号，不要使用 Python None/True/False，必须使用 JSON null/true/false。
5. 所有字符串必须使用双引号；字符串内部换行必须写成两个字符：反斜杠+n，即 \\n。
6. 不确定的信息用 "未知"、[] 或 null，不要省略当前阶段模板要求的字段。
7. 不要为了简短删除必填字段；宁可字段值为空数组，也要保留字段。
8. 不要把 JSON 放入数组顶层；顶层必须是 object。
9. 只输出当前阶段提示词模板需要的字段；不要额外添加说明字段、调试字段、思考字段、analysis 字段、reasoning 字段。
10. 输入里的 _local_model_output_contract 只是约束说明，绝对不能复制到输出 JSON。
11. 严禁复述完整原文、完整 paragraphs、完整 stage_outputs；只引用必要短证据。
12. 数组必须克制：除非阶段提示词明确要求逐条完整输出，否则单个数组建议不超过 80 项。
13. 字符串必须短：说明类字段尽量 1-3 句；不要写长篇分析散文。
14. 如果内容很多，优先输出结构化摘要、id、短证据、风险点，不要输出大段原文。
15. 输出前自检：JSON 能被 json.loads 直接解析，没有模板外多余顶层字段，没有超长无意义文本。
""".strip()

INTERNAL_OUTPUT_FIELD_NAMES = {
    "_local_model_output_contract",
    "analysis",
    "reasoning",
    "chain_of_thought",
    "scratchpad",
    "thoughts",
    "thinking",
    "internal_reasoning",
    "internal_notes",
    "debug",
    "debug_notes",
}


def apply_json_guard(system_prompt: str, stage_id: str | None = None) -> str:
    stage_line = f"\n\n当前阶段：{stage_id}" if stage_id else ""
    return f"{LOCAL_GEMMA_JSON_GUARD}{stage_line}\n\n---\n\n{system_prompt.strip()}"


def compact_payload_hint(payload: dict[str, Any]) -> dict[str, Any]:
    """Add a lightweight hint without mutating the business payload semantics."""
    return {
        "_local_model_output_contract": {
            "format": "json_object_only",
            "no_markdown": True,
            "keep_required_fields": True,
            "do_not_copy_this_field_to_output": True,
            "do_not_repeat_full_input": True,
            "avoid_long_arrays_unless_required": True,
            "avoid_long_strings": True,
        },
        **payload,
    }


def remove_internal_output_fields(value: Any) -> Any:
    """Remove guard / reasoning fields that local or remote models may copy into business JSON.

    The prompt guard asks models not to emit these fields, but this is the final
    runtime safety net after json.loads and JSON repair. It is intentionally
    recursive because copied control fields often appear inside nested objects.
    """
    if isinstance(value, dict):
        return {
            key: remove_internal_output_fields(item)
            for key, item in value.items()
            if key not in INTERNAL_OUTPUT_FIELD_NAMES and not key.startswith("_local_model_")
        }
    if isinstance(value, list):
        return [remove_internal_output_fields(item) for item in value]
    return value
