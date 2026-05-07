from __future__ import annotations

from typing import Any

LOCAL_GEMMA_JSON_GUARD = """
# 本地 Gemma JSON 输出护栏

你运行在本地量化模型环境，默认模型可能是 Gemma 4 31B Q4。为保证自动流水线稳定，必须严格遵守：

1. 只输出一个合法 JSON object。
2. 第一个非空字符必须是 {，最后一个非空字符必须是 }。
3. 不要输出 Markdown，不要输出 ```json，不要输出解释、前言、后记、免责声明。
4. 不要输出注释，不要使用单引号，不要使用 Python None/True/False，必须使用 JSON null/true/false。
5. 所有字符串必须使用双引号；字符串内部换行必须写成两个字符：反斜杠+n，即 \\n。
6. 不确定的信息用 "未知"、[] 或 null，不要省略模板要求的字段。
7. 不要为了简短删除必填字段；宁可字段值为空数组，也要保留字段。
8. 不要把 JSON 放入数组顶层；顶层必须是 object。
9. 输出前自检：JSON 能被 json.loads 直接解析。
""".strip()


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
        },
        **payload,
    }
