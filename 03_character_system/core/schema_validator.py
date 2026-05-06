from __future__ import annotations

from typing import Any

REQUIRED_TOP = [
    "schema_version", "module", "status", "stage_mode", "characters", "alias_index",
    "character_script_usage", "quality_report", "schema_validation"
]
REQUIRED_CHARACTER_FIELDS = [
    "character_id", "canonical_name", "aliases", "gender", "age_range", "identity",
    "appearance", "costume", "temperament", "role_function", "source_evidence", "usage_in_script"
]


def validate_final_output(data: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in REQUIRED_TOP:
        if field not in data:
            issues.append(f"缺少顶层字段：{field}")
    characters = data.get("characters", [])
    if not isinstance(characters, list) or not characters:
        issues.append("characters 为空或不是数组")
        characters = []
    ids: set[str] = set()
    names: set[str] = set()
    aliases_seen: dict[str, str] = {}
    for idx, item in enumerate(characters):
        if not isinstance(item, dict):
            issues.append(f"characters[{idx}] 不是对象")
            continue
        for field in REQUIRED_CHARACTER_FIELDS:
            if item.get(field) in (None, "", [], {}):
                issues.append(f"角色 {item.get('canonical_name', idx)} 缺少必要字段：{field}")
        cid = str(item.get("character_id", "")).strip()
        name = str(item.get("canonical_name", "")).strip()
        if cid in ids:
            issues.append(f"character_id 重复：{cid}")
        if cid:
            ids.add(cid)
        if name in names:
            issues.append(f"canonical_name 重复：{name}")
        if name:
            names.add(name)
        if any(prefix in name for prefix in ["年轻", "少年", "中年", "老年", "年老"]):
            issues.append(f"禁止按年龄段拆角色：{name}")
        for alias in item.get("aliases", []) or []:
            alias_key = str(alias).strip()
            if not alias_key:
                continue
            prev = aliases_seen.get(alias_key)
            if prev and prev != name:
                issues.append(f"同一别名被多个角色占用：{alias_key} -> {prev} / {name}")
            aliases_seen[alias_key] = name
        if not isinstance(item.get("source_evidence"), list) or not item.get("source_evidence"):
            issues.append(f"角色缺少证据链：{name or cid}")
        if not isinstance(item.get("usage_in_script"), list):
            issues.append(f"usage_in_script 必须为数组：{name or cid}")
    return {"passed": not issues, "issues": issues}
