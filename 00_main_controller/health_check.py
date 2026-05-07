from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PIPELINE_ORDER = [
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
    "07_storyboard_image",
    "08_audio",
    "09_video",
    "10_final_assembly",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _check_python(checks: list[dict[str, Any]]) -> None:
    checks.append({
        "group": "Python",
        "check_id": "python_version",
        "status": "passed" if sys.version_info >= (3, 10) else "warning",
        "message": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "fix_hint": "建议使用 Python 3.10+" if sys.version_info < (3, 10) else "",
    })
    checks.append({
        "group": "Python",
        "check_id": "working_directory",
        "status": "passed" if ROOT.exists() else "failed",
        "message": f"工作目录: {ROOT}",
        "fix_hint": "" if ROOT.exists() else "请从项目根目录运行",
    })
    try:
        import_module("00_common.io_utils")
        checks.append({"group": "Python", "check_id": "import_00_common", "status": "passed", "message": "00_common 可导入", "fix_hint": ""})
    except Exception as exc:
        checks.append({"group": "Python", "check_id": "import_00_common", "status": "failed", "message": f"00_common 导入失败: {exc}", "fix_hint": "确保从项目根目录运行，或检查 PYTHONPATH"})


def _check_pipeline(checks: list[dict[str, Any]]) -> None:
    pipeline_json = ROOT / "pipeline.json"
    checks.append({
        "group": "Pipeline",
        "check_id": "pipeline_json_exists",
        "status": "passed" if pipeline_json.exists() else "warning",
        "message": f"pipeline.json {'存在' if pipeline_json.exists() else '不存在'}",
        "fix_hint": "" if pipeline_json.exists() else "pipeline.json 不影响运行，但建议保留",
    })
    for module_name in PIPELINE_ORDER:
        module_dir = ROOT / module_name
        run_staged = module_dir / "run_staged.py"
        dir_ok = module_dir.exists()
        staged_ok = run_staged.exists()
        status = "passed" if dir_ok and staged_ok else "failed"
        msg = f"{module_name}: 目录{'存在' if dir_ok else '缺失'}"
        if dir_ok:
            msg += f", run_staged.py{'存在' if staged_ok else '缺失'}"
        checks.append({
            "group": "Pipeline",
            "check_id": f"module_{module_name}",
            "status": status,
            "message": msg,
            "fix_hint": "" if status == "passed" else f"请确保 {module_name}/ 目录和 run_staged.py 存在",
        })


def _check_contracts(checks: list[dict[str, Any]]) -> None:
    contracts_path = ROOT / "configs" / "module_contracts.json"
    if not contracts_path.exists():
        checks.append({"group": "Contracts", "check_id": "contracts_json_exists", "status": "warning", "message": "configs/module_contracts.json 不存在", "fix_hint": "不影响运行，但建议保留"})
        return
    checks.append({"group": "Contracts", "check_id": "contracts_json_exists", "status": "passed", "message": "configs/module_contracts.json 存在", "fix_hint": ""})
    try:
        data = json.loads(contracts_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            checks.append({"group": "Contracts", "check_id": "contracts_format", "status": "warning", "message": "contracts 格式不是 dict", "fix_hint": ""})
            return
        for module_name in PIPELINE_ORDER:
            contract = data.get(module_name)
            if not isinstance(contract, dict):
                modules = data.get("modules", {})
                if isinstance(modules, dict):
                    contract = modules.get(module_name)
            if not isinstance(contract, dict):
                checks.append({"group": "Contracts", "check_id": f"contract_{module_name}", "status": "warning", "message": f"{module_name} 无 contract 定义", "fix_hint": ""})
                continue
            has_requires = "requires" in contract
            has_produces = "produces" in contract
            status = "passed" if has_requires and has_produces else "warning"
            checks.append({
                "group": "Contracts",
                "check_id": f"contract_{module_name}",
                "status": status,
                "message": f"{module_name}: requires={'有' if has_requires else '无'}, produces={'有' if has_produces else '无'}",
                "fix_hint": "" if status == "passed" else f"建议为 {module_name} 添加 requires 和 produces 定义",
            })
    except Exception as exc:
        checks.append({"group": "Contracts", "check_id": "contracts_parse", "status": "warning", "message": f"contracts 解析失败: {exc}", "fix_hint": ""})


def _check_llm(checks: list[dict[str, Any]]) -> None:
    base_url = os.getenv("AI_DRAMA_LLM_BASE_URL", "").strip()
    model = os.getenv("AI_DRAMA_LLM_MODEL", "").strip()
    api_key = os.getenv("AI_DRAMA_LLM_API_KEY", "").strip()
    timeout = os.getenv("AI_DRAMA_LLM_TIMEOUT_SEC", "120").strip()

    checks.append({
        "group": "LLM",
        "check_id": "llm_base_url",
        "status": "passed" if base_url else "warning",
        "message": f"AI_DRAMA_LLM_BASE_URL={'已设置' if base_url else '未设置（使用默认 DeepSeek）'}",
        "fix_hint": "" if base_url else "如使用本地模型，请设置 AI_DRAMA_LLM_BASE_URL",
    })
    checks.append({
        "group": "LLM",
        "check_id": "llm_model",
        "status": "passed" if model else "warning",
        "message": f"AI_DRAMA_LLM_MODEL={'已设置: ' + model if model else '未设置'}",
        "fix_hint": "" if model else "请设置 AI_DRAMA_LLM_MODEL",
    })

    is_local = any(host in base_url for host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")) if base_url else False
    needs_api_key = not is_local and (not base_url or "api." in base_url or "deepseek" in base_url.lower())
    if needs_api_key:
        checks.append({
            "group": "LLM",
            "check_id": "llm_api_key",
            "status": "passed" if api_key else "warning",
            "message": f"AI_DRAMA_LLM_API_KEY={'已设置' if api_key else '未设置'}（云端模式需要）",
            "fix_hint": "" if api_key else "使用云端 LLM 需要设置 AI_DRAMA_LLM_API_KEY；如使用本地模型，请设置 AI_DRAMA_LLM_BASE_URL",
        })
    else:
        checks.append({"group": "LLM", "check_id": "llm_api_key", "status": "passed", "message": "本地 LLM 模式，不要求 API Key", "fix_hint": ""})

    if base_url and api_key or (base_url and is_local):
        chat_url = base_url.rstrip("/")
        if "/chat/completions" not in chat_url:
            chat_url = chat_url.rstrip("/") + "/v1/chat/completions"
        try:
            payload = json.dumps({
                "model": model or "test",
                "messages": [{"role": "user", "content": "Reply with exactly: {\"ok\":true}"}],
                "max_tokens": 16,
                "temperature": 0,
            }).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            req = urllib.request.Request(chat_url, data=payload, headers=headers, method="POST")
            timeout_sec = min(int(timeout) if timeout.isdigit() else 120, 30)
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
                content = ""
                choices = body.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content", "")
                try:
                    parsed = json.loads(content)
                    is_ok = parsed.get("ok") is True
                except Exception:
                    is_ok = "ok" in content.lower() or "true" in content.lower()
                checks.append({
                    "group": "LLM",
                    "check_id": "llm_test_request",
                    "status": "passed" if is_ok else "warning",
                    "message": f"LLM 测试请求{'成功' if is_ok else '返回异常'}: {content[:80]}",
                    "fix_hint": "" if is_ok else "LLM 返回内容不符合预期，但可能仍可用",
                })
        except Exception as exc:
            checks.append({
                "group": "LLM",
                "check_id": "llm_test_request",
                "status": "warning",
                "message": f"LLM 测试请求失败: {exc}",
                "fix_hint": "请检查 LLM 服务是否启动、URL 是否正确",
            })
    else:
        checks.append({"group": "LLM", "check_id": "llm_test_request", "status": "warning", "message": "LLM 未配置，跳过测试请求", "fix_hint": "请设置 AI_DRAMA_LLM_BASE_URL 和 AI_DRAMA_LLM_MODEL"})


def _check_comfyui(checks: list[dict[str, Any]]) -> None:
    comfyui_url = os.getenv("AI_DRAMA_COMFYUI_BASE_URL", "").strip()
    workflow_path = os.getenv("AI_DRAMA_VIDEO_COMFYUI_WORKFLOW", os.getenv("AI_DRAMA_COMFYUI_WORKFLOW", "")).strip()
    mapping_path = os.getenv("AI_DRAMA_COMFYUI_WORKFLOW_MAPPING", "").strip()

    checks.append({
        "group": "ComfyUI",
        "check_id": "comfyui_base_url",
        "status": "passed" if comfyui_url else "warning",
        "message": f"AI_DRAMA_COMFYUI_BASE_URL={'已设置: ' + comfyui_url if comfyui_url else '未设置'}",
        "fix_hint": "" if comfyui_url else "如需视频生成，请设置 AI_DRAMA_COMFYUI_BASE_URL",
    })

    if comfyui_url:
        try:
            req = urllib.request.Request(f"{comfyui_url.rstrip('/')}/system_stats", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                checks.append({
                    "group": "ComfyUI",
                    "check_id": "comfyui_reachable",
                    "status": "passed" if resp.status == 200 else "failed",
                    "message": f"ComfyUI 可访问 ({resp.status})",
                    "fix_hint": "",
                })
        except Exception as exc:
            checks.append({
                "group": "ComfyUI",
                "check_id": "comfyui_reachable",
                "status": "failed",
                "message": f"ComfyUI 不可访问: {exc}",
                "fix_hint": f"请确保 ComfyUI 服务在 {comfyui_url} 运行",
            })
    else:
        checks.append({"group": "ComfyUI", "check_id": "comfyui_reachable", "status": "warning", "message": "ComfyUI URL 未设置，跳过可达性检查", "fix_hint": ""})

    if workflow_path:
        checks.append({
            "group": "ComfyUI",
            "check_id": "workflow_file",
            "status": "passed" if Path(workflow_path).exists() else "failed",
            "message": f"workflow 文件{'存在' if Path(workflow_path).exists() else '不存在'}: {workflow_path}",
            "fix_hint": "" if Path(workflow_path).exists() else f"请创建 workflow 文件: {workflow_path}",
        })
    else:
        checks.append({"group": "ComfyUI", "check_id": "workflow_file", "status": "warning", "message": "workflow 文件路径未设置", "fix_hint": "设置 AI_DRAMA_VIDEO_COMFYUI_WORKFLOW"})

    if mapping_path:
        checks.append({
            "group": "ComfyUI",
            "check_id": "mapping_file",
            "status": "passed" if Path(mapping_path).exists() else "failed",
            "message": f"mapping 文件{'存在' if Path(mapping_path).exists() else '不存在'}: {mapping_path}",
            "fix_hint": "" if Path(mapping_path).exists() else f"请创建 mapping 文件: {mapping_path}",
        })
    else:
        checks.append({"group": "ComfyUI", "check_id": "mapping_file", "status": "warning", "message": "mapping 文件路径未设置", "fix_hint": "设置 AI_DRAMA_COMFYUI_WORKFLOW_MAPPING"})


def _check_audio(checks: list[dict[str, Any]]) -> None:
    tts_root = os.getenv("AI_DRAMA_INDEX_TTS_ROOT", "").strip()
    if not tts_root:
        default_tts = ROOT / "index-tts"
        tts_root = str(default_tts) if default_tts.exists() else ""

    checks.append({
        "group": "Audio",
        "check_id": "tts_root",
        "status": "passed" if tts_root and Path(tts_root).exists() else "warning",
        "message": f"TTS 根目录{'存在' if tts_root and Path(tts_root).exists() else '不存在'}: {tts_root or '(未设置)'}",
        "fix_hint": "" if tts_root and Path(tts_root).exists() else "设置 AI_DRAMA_INDEX_TTS_ROOT 或确保 index-tts 目录存在",
    })

    if tts_root and Path(tts_root).exists():
        tts_path = Path(tts_root)
        checkpoints = tts_path / "checkpoints"
        checks.append({
            "group": "Audio",
            "check_id": "tts_checkpoints",
            "status": "passed" if checkpoints.exists() else "warning",
            "message": f"checkpoints 目录{'存在' if checkpoints.exists() else '不存在'}",
            "fix_hint": "" if checkpoints.exists() else "请确保 TTS checkpoints 目录存在",
        })
        voices_json = ROOT / "shared_assets" / "voice_library" / "voices.json"
        checks.append({
            "group": "Audio",
            "check_id": "voices_json",
            "status": "passed" if voices_json.exists() else "warning",
            "message": f"voices.json {'存在' if voices_json.exists() else '不存在'}",
            "fix_hint": "" if voices_json.exists() else "请确保 shared_assets/voice_library/voices.json 存在",
        })
    else:
        checks.append({"group": "Audio", "check_id": "tts_checkpoints", "status": "warning", "message": "TTS 根目录不存在，跳过 checkpoints 检查", "fix_hint": ""})
        checks.append({"group": "Audio", "check_id": "voices_json", "status": "warning", "message": "TTS 根目录不存在，跳过 voices.json 检查", "fix_hint": ""})


def _check_video_final(checks: list[dict[str, Any]]) -> None:
    ffmpeg_bin = os.getenv("AI_DRAMA_FFMPEG", "ffmpeg")
    ffprobe_bin = os.getenv("AI_DRAMA_FFPROBE", "ffprobe")
    ffmpeg_ok = bool(shutil.which(ffmpeg_bin))
    ffprobe_ok = bool(shutil.which(ffprobe_bin))
    checks.append({
        "group": "Video/Final",
        "check_id": "ffmpeg",
        "status": "passed" if ffmpeg_ok else "failed",
        "message": f"ffmpeg {'可用' if ffmpeg_ok else '不可用'}: {ffmpeg_bin}",
        "fix_hint": "" if ffmpeg_ok else "请安装 ffmpeg 并添加到 PATH，或设置 AI_DRAMA_FFMPEG",
    })
    checks.append({
        "group": "Video/Final",
        "check_id": "ffprobe",
        "status": "passed" if ffprobe_ok else "failed",
        "message": f"ffprobe {'可用' if ffprobe_ok else '不可用'}: {ffprobe_bin}",
        "fix_hint": "" if ffprobe_ok else "请安装 ffprobe 并添加到 PATH，或设置 AI_DRAMA_FFPROBE",
    })


def _check_workspace(checks: list[dict[str, Any]], project_id: str | None = None) -> None:
    workspace = ROOT / "workspace"
    projects_dir = workspace / "projects"
    shared_assets = ROOT / "shared_assets"

    projects_writable = False
    if projects_dir.exists():
        try:
            test_file = projects_dir / ".health_check_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            projects_writable = True
        except Exception:
            projects_writable = False

    checks.append({
        "group": "Workspace",
        "check_id": "projects_writable",
        "status": "passed" if projects_writable else "failed",
        "message": f"workspace/projects {'可写' if projects_writable else '不可写'}",
        "fix_hint": "" if projects_writable else "请确保 workspace/projects 目录存在且可写",
    })

    shared_writable = False
    if shared_assets.exists():
        try:
            test_file = shared_assets / ".health_check_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            shared_writable = True
        except Exception:
            shared_writable = False

    checks.append({
        "group": "Workspace",
        "check_id": "shared_assets_writable",
        "status": "passed" if shared_writable else "warning",
        "message": f"shared_assets {'可写' if shared_writable else '不可写'}",
        "fix_hint": "" if shared_writable else "请确保 shared_assets 目录可写",
    })

    if project_id:
        project_dir = projects_dir / project_id
        if project_dir.exists():
            checks.append({
                "group": "Workspace",
                "check_id": "project_dir",
                "status": "passed",
                "message": f"项目目录存在: {project_id}",
                "fix_hint": "",
            })
            input_dir = project_dir / "input"
            checks.append({
                "group": "Workspace",
                "check_id": "project_input",
                "status": "passed" if input_dir.exists() else "warning",
                "message": f"项目 input 目录{'存在' if input_dir.exists() else '不存在'}",
                "fix_hint": "" if input_dir.exists() else "请确保项目 input 目录存在",
            })
        else:
            checks.append({
                "group": "Workspace",
                "check_id": "project_dir",
                "status": "warning",
                "message": f"项目目录不存在: {project_id}",
                "fix_hint": f"请先创建项目: {project_id}",
            })


def run_health_check(project_id: str | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    _check_python(checks)
    _check_pipeline(checks)
    _check_contracts(checks)
    _check_llm(checks)
    _check_comfyui(checks)
    _check_audio(checks)
    _check_video_final(checks)
    _check_workspace(checks, project_id)

    passed_count = sum(1 for c in checks if c["status"] == "passed")
    warning_count = sum(1 for c in checks if c["status"] == "warning")
    failed_count = sum(1 for c in checks if c["status"] == "failed")

    if failed_count > 0:
        overall = "failed"
    elif warning_count > 0:
        overall = "warning"
    else:
        overall = "passed"

    result = {
        "status": overall,
        "created_at": _now_iso(),
        "checks": checks,
        "summary": {
            "passed": passed_count,
            "warning": warning_count,
            "failed": failed_count,
        },
    }

    output_dir = ROOT / "workspace"
    if project_id:
        project_dir = output_dir / "projects" / project_id
        if project_dir.exists():
            output_dir = project_dir
    output_path = output_dir / "system_health_report.json"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()
    result = run_health_check(args.project_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
