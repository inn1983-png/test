from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "props", "prop_alias_index",
    "prop_script_usage", "quality_report", "schema_validation"
]
REQUIRED_PROP_FIELDS = [
    "prop_id", "canonical_prop_name", "aliases", "prop_type", "owner_character",
    "usage_function", "appearance", "material", "risk_notes", "source_evidence", "usage_in_script"
]


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    props = data.get("props", [])
    if not isinstance(props, list) or not props:
        issues.append("props 为空或不是数组")
        props = []
    ids: set[str] = set()
    names: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for idx, item in enumerate(props):
        if not isinstance(item, dict):
            issues.append(f"props[{idx}] 不是对象")
            continue
        for field in REQUIRED_PROP_FIELDS:
            if item.get(field) in (None, "", [], {}):
                issues.append(f"道具 {item.get('canonical_prop_name', idx)} 缺少必要字段：{field}")
        if "prompt" in item or "image_prompt" in item or "desc_prompt" in item:
            issues.append(f"道具含图像提示词字段，越界：{item.get('canonical_prop_name', idx)}")
        pid = str(item.get("prop_id", "")).strip()
        name = str(item.get("canonical_prop_name", "")).strip()
        if pid in ids:
            issues.append(f"prop_id 重复：{pid}")
        if pid:
            ids.add(pid)
        if name in names:
            issues.append(f"canonical_prop_name 重复：{name}")
        if name:
            names.add(name)
        for alias in item.get("aliases", []) or []:
            alias_key = str(alias).strip()
            if not alias_key:
                continue
            prev = aliases_seen.get(alias_key)
            if prev and prev != name:
                issues.append(f"同一道具别名被多个道具占用：{alias_key} -> {prev} / {name}")
            aliases_seen[alias_key] = name
        if not isinstance(item.get("source_evidence"), list) or not item.get("source_evidence"):
            issues.append(f"道具缺少证据链：{name or pid}")
        if not isinstance(item.get("usage_in_script"), list):
            issues.append(f"usage_in_script 必须为数组：{name or pid}")
    return {"passed": not issues, "issues": issues}
