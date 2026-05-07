from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = int(os.getenv("AI_DRAMA_UI_PORT", "7860"))
MODULES_00_06 = [
    "01_novel_parser",
    "02_script_writer",
    "03_character_system",
    "04_scene_system",
    "05_prop_system",
    "06_storyboard",
]
KEY_OUTPUTS = {
    "01_novel_parser": ["novel_analysis.json", "novel_meta.json"],
    "02_script_writer": ["script.json", "script.txt", "script_meta.json"],
    "03_character_system": ["characters.json", "characters_meta.json"],
    "04_scene_system": ["scenes.json", "scenes_meta.json"],
    "05_prop_system": ["props.json", "props_meta.json"],
    "06_storyboard": ["storyboard.json", "storyboard_meta.json"],
}

STATE_LOCK = threading.Lock()
STATE: dict[str, Any] = {
    "running": False,
    "current_task": "",
    "started_at": None,
    "finished_at": None,
    "last_returncode": None,
    "logs": [],
}


def _project_dir(project_id: str) -> Path:
    return ROOT_DIR / "workspace" / "projects" / project_id


def _input_file(project_id: str) -> Path:
    return _project_dir(project_id) / "input" / "novel.txt"


def _append_log(line: str) -> None:
    with STATE_LOCK:
        logs = STATE.setdefault("logs", [])
        logs.append(line.rstrip())
        if len(logs) > 800:
            del logs[: len(logs) - 800]


def _set_state(**kwargs: Any) -> None:
    with STATE_LOCK:
        STATE.update(kwargs)


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200) -> None:
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _text_response(handler: BaseHTTPRequestHandler, text: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
    raw = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _read_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _safe_project_id(value: str) -> str:
    clean = "".join(ch for ch in value.strip() if ch.isalnum() or ch in "_-.")
    return clean or "project_test_001"


def _run_command(args: list[str], task_name: str) -> None:
    if STATE.get("running"):
        return
    _set_state(running=True, current_task=task_name, started_at=time.time(), finished_at=None, last_returncode=None, logs=[])
    _append_log(f"开始：{task_name}")
    _append_log("命令：" + " ".join(args))
    try:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        process = subprocess.Popen(
            args,
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            _append_log(line)
        code = process.wait()
        _append_log(f"结束：returncode={code}")
        _set_state(last_returncode=code)
    except Exception as exc:  # noqa: BLE001
        _append_log(f"运行失败：{exc}")
        _set_state(last_returncode=-1)
    finally:
        _set_state(running=False, finished_at=time.time())


def _start_thread(args: list[str], task_name: str) -> bool:
    with STATE_LOCK:
        if STATE.get("running"):
            return False
    thread = threading.Thread(target=_run_command, args=(args, task_name), daemon=True)
    thread.start()
    return True


def _module_status(project_id: str, module: str) -> dict[str, Any]:
    module_dir = _project_dir(project_id) / module
    outputs = []
    exists_any = False
    status = "not_run"
    for filename in KEY_OUTPUTS.get(module, []):
        path = module_dir / filename
        item = {"filename": filename, "exists": path.exists(), "path": str(path.relative_to(ROOT_DIR)) if path.exists() else ""}
        if path.exists():
            exists_any = True
            item["size"] = path.stat().st_size
            item["mtime"] = path.stat().st_mtime
            if filename.endswith(".json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    item["json_status"] = data.get("status")
                    item["schema_passed"] = (data.get("schema_validation") or {}).get("passed")
                    qr = data.get("quality_report") or {}
                    item["needs_review"] = qr.get("needs_review")
                except Exception as exc:  # noqa: BLE001
                    item["read_error"] = str(exc)
        outputs.append(item)
    if exists_any:
        status = "done"
        for item in outputs:
            if item.get("json_status") == "needs_review" or item.get("needs_review"):
                status = "needs_review"
                break
    return {"module": module, "status": status, "outputs": outputs}


def _read_output(project_id: str, module: str, filename: str) -> dict[str, Any]:
    if module not in KEY_OUTPUTS or filename not in KEY_OUTPUTS[module]:
        return {"error": "不允许读取该文件"}
    path = _project_dir(project_id) / module / filename
    if not path.exists():
        return {"error": "文件不存在", "path": str(path.relative_to(ROOT_DIR))}
    text = path.read_text(encoding="utf-8", errors="replace")
    parsed: Any = None
    if filename.endswith(".json"):
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
    return {"path": str(path.relative_to(ROOT_DIR)), "text": text, "json": parsed}


HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AI Drama 00-06 测试控制台</title>
<style>
:root { --bg:#0f172a; --panel:#111827; --muted:#94a3b8; --text:#e5e7eb; --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444; --blue:#60a5fa; }
* { box-sizing: border-box; }
body { margin:0; background:linear-gradient(180deg,#0f172a,#020617); color:var(--text); font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
header { padding:22px 28px; border-bottom:1px solid #1f2937; background:rgba(15,23,42,.88); position:sticky; top:0; z-index:2; }
h1 { margin:0 0 6px; font-size:24px; }
small { color:var(--muted); }
main { max-width:1200px; margin:0 auto; padding:22px; display:grid; gap:18px; }
.card { background:rgba(17,24,39,.88); border:1px solid #243244; border-radius:16px; padding:18px; box-shadow:0 10px 30px rgba(0,0,0,.22); }
.row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
input, textarea, select { background:#020617; color:var(--text); border:1px solid #334155; border-radius:10px; padding:10px 12px; font-size:14px; }
input { min-width:260px; }
textarea { width:100%; min-height:170px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
button { border:0; border-radius:10px; padding:10px 14px; background:#2563eb; color:white; cursor:pointer; font-weight:600; }
button.secondary { background:#334155; }
button.warn { background:#b45309; }
button:disabled { opacity:.45; cursor:not-allowed; }
.grid { display:grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap:10px; }
.mod { border:1px solid #334155; border-radius:14px; padding:12px; background:#020617; }
.mod h3 { margin:0 0 8px; font-size:14px; }
.badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:12px; color:#020617; background:var(--muted); }
.badge.done { background:var(--ok); }
.badge.needs_review { background:var(--warn); }
.badge.not_run { background:#64748b; }
pre { white-space:pre-wrap; word-break:break-word; background:#020617; border:1px solid #334155; border-radius:12px; padding:12px; max-height:460px; overflow:auto; }
.tabs { display:flex; gap:8px; flex-wrap:wrap; }
.linkbtn { background:#1e293b; color:#dbeafe; border:1px solid #334155; }
.kv { display:grid; grid-template-columns:140px 1fr; gap:8px; color:var(--muted); }
.footer-note { color:var(--muted); font-size:13px; line-height:1.7; }
@media (max-width: 900px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
</head>
<body>
<header>
  <h1>AI Drama 00–06 测试控制台</h1>
  <small>本地网页，只负责测试和查看结果；不改变 01–06 核心逻辑。</small>
</header>
<main>
  <section class="card">
    <h2>1. 项目与小说输入</h2>
    <div class="row">
      <label>项目 ID：<input id="projectId" value="project_test_001" /></label>
      <button onclick="saveInput()">保存小说输入</button>
      <button class="secondary" onclick="refreshAll()">刷新状态</button>
    </div>
    <p class="footer-note">小说会保存到 <code>workspace/projects/{项目ID}/input/novel.txt</code>。</p>
    <textarea id="novelText" placeholder="把小说章节粘贴到这里，然后点“保存小说输入”。如果你已经手动放好了 novel.txt，可以不填。"></textarea>
  </section>

  <section class="card">
    <h2>2. 运行 00–06</h2>
    <div class="row">
      <button onclick="runAll()" id="runAllBtn">一键运行 01–06</button>
      <select id="moduleSelect">
        <option value="01_novel_parser">01 小说解析</option>
        <option value="02_script_writer">02 剧本改编</option>
        <option value="03_character_system">03 角色库</option>
        <option value="04_scene_system">04 场景库</option>
        <option value="05_prop_system">05 道具库</option>
        <option value="06_storyboard">06 单帧分镜</option>
      </select>
      <button class="secondary" onclick="runModule()" id="runModuleBtn">只运行选中模块</button>
    </div>
    <div class="kv" style="margin-top:12px">
      <div>当前任务</div><div id="currentTask">-</div>
      <div>运行状态</div><div id="runningState">-</div>
      <div>最后返回码</div><div id="returnCode">-</div>
    </div>
  </section>

  <section class="card">
    <h2>3. 模块状态</h2>
    <div class="grid" id="moduleGrid"></div>
  </section>

  <section class="card">
    <h2>4. 查看输出</h2>
    <div class="row">
      <select id="outputModule" onchange="fillFileOptions()"></select>
      <select id="outputFile"></select>
      <button onclick="loadOutput()">查看</button>
    </div>
    <pre id="outputBox">等待选择输出文件...</pre>
  </section>

  <section class="card">
    <h2>5. 运行日志</h2>
    <pre id="logBox">等待运行...</pre>
  </section>
</main>
<script>
const modules = ["01_novel_parser","02_script_writer","03_character_system","04_scene_system","05_prop_system","06_storyboard"];
const outputFiles = {
  "01_novel_parser": ["novel_analysis.json", "novel_meta.json"],
  "02_script_writer": ["script.json", "script.txt", "script_meta.json"],
  "03_character_system": ["characters.json", "characters_meta.json"],
  "04_scene_system": ["scenes.json", "scenes_meta.json"],
  "05_prop_system": ["props.json", "props_meta.json"],
  "06_storyboard": ["storyboard.json", "storyboard_meta.json"]
};
function pid(){ return document.getElementById('projectId').value.trim() || 'project_test_001'; }
async function api(path, options={}){
  const res = await fetch(path, options);
  return await res.json();
}
async function saveInput(){
  const body = {project_id: pid(), text: document.getElementById('novelText').value};
  const data = await api('/api/save_input', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  alert(data.ok ? '已保存：' + data.path : '保存失败：' + data.error);
  refreshAll();
}
async function runAll(){
  const data = await api('/api/run_all', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({project_id: pid()})});
  if(!data.ok) alert(data.error || '启动失败');
  refreshAll();
}
async function runModule(){
  const module = document.getElementById('moduleSelect').value;
  const data = await api('/api/run_module', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({project_id: pid(), module})});
  if(!data.ok) alert(data.error || '启动失败');
  refreshAll();
}
function fillFileOptions(){
  const m = document.getElementById('outputModule').value;
  const f = document.getElementById('outputFile');
  f.innerHTML = '';
  for(const name of outputFiles[m] || []){
    const opt = document.createElement('option'); opt.value = name; opt.textContent = name; f.appendChild(opt);
  }
}
function initSelectors(){
  const sel = document.getElementById('outputModule');
  sel.innerHTML = '';
  for(const m of modules){ const opt = document.createElement('option'); opt.value = m; opt.textContent = m; sel.appendChild(opt); }
  fillFileOptions();
}
async function loadOutput(){
  const m = document.getElementById('outputModule').value;
  const f = document.getElementById('outputFile').value;
  const data = await api(`/api/output?project_id=${encodeURIComponent(pid())}&module=${encodeURIComponent(m)}&file=${encodeURIComponent(f)}`);
  const box = document.getElementById('outputBox');
  if(data.error){ box.textContent = data.error + '\n' + (data.path || ''); return; }
  if(data.json){ box.textContent = JSON.stringify(data.json, null, 2); }
  else { box.textContent = data.text || ''; }
}
async function refreshAll(){
  const data = await api('/api/status?project_id=' + encodeURIComponent(pid()));
  document.getElementById('currentTask').textContent = data.state.current_task || '-';
  document.getElementById('runningState').textContent = data.state.running ? '运行中' : '空闲';
  document.getElementById('returnCode').textContent = data.state.last_returncode ?? '-';
  document.getElementById('runAllBtn').disabled = data.state.running;
  document.getElementById('runModuleBtn').disabled = data.state.running;
  const grid = document.getElementById('moduleGrid'); grid.innerHTML = '';
  for(const item of data.modules){
    const div = document.createElement('div'); div.className = 'mod';
    const files = item.outputs.map(o => `${o.exists ? '✅' : '—'} ${o.filename}${o.json_status ? ' / ' + o.json_status : ''}`).join('<br>');
    div.innerHTML = `<h3>${item.module}</h3><span class="badge ${item.status}">${item.status}</span><p style="font-size:12px;color:#94a3b8;line-height:1.7">${files}</p>`;
    grid.appendChild(div);
  }
  document.getElementById('logBox').textContent = (data.state.logs || []).join('\n') || '等待运行...';
}
initSelectors(); refreshAll(); setInterval(refreshAll, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            _text_response(self, HTML)
            return
        if parsed.path == "/api/status":
            query = parse_qs(parsed.query)
            project_id = _safe_project_id(query.get("project_id", ["project_test_001"])[0])
            with STATE_LOCK:
                state = dict(STATE)
                state["logs"] = list(STATE.get("logs", []))
            data = {
                "project_id": project_id,
                "input_exists": _input_file(project_id).exists(),
                "modules": [_module_status(project_id, module) for module in MODULES_00_06],
                "state": state,
            }
            _json_response(self, data)
            return
        if parsed.path == "/api/output":
            query = parse_qs(parsed.query)
            project_id = _safe_project_id(query.get("project_id", ["project_test_001"])[0])
            module = query.get("module", [""])[0]
            filename = query.get("file", [""])[0]
            _json_response(self, _read_output(project_id, module, filename))
            return
        _json_response(self, {"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = _read_body(self)
        project_id = _safe_project_id(str(body.get("project_id", "project_test_001")))
        if parsed.path == "/api/save_input":
            text = str(body.get("text", ""))
            if not text.strip():
                _json_response(self, {"ok": False, "error": "小说内容为空"}, status=400)
                return
            path = _input_file(project_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            _json_response(self, {"ok": True, "path": str(path.relative_to(ROOT_DIR))})
            return
        if parsed.path == "/api/run_all":
            args = [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--from-module", "01_novel_parser", "--to-module", "06_storyboard"]
            ok = _start_thread(args, f"运行 01–06：{project_id}")
            _json_response(self, {"ok": ok, "error": "已有任务正在运行" if not ok else ""})
            return
        if parsed.path == "/api/run_module":
            module = str(body.get("module", ""))
            if module not in MODULES_00_06:
                _json_response(self, {"ok": False, "error": "模块不允许"}, status=400)
                return
            args = [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", project_id, "--only-module", module]
            ok = _start_thread(args, f"运行 {module}：{project_id}")
            _json_response(self, {"ok": ok, "error": "已有任务正在运行" if not ok else ""})
            return
        _json_response(self, {"error": "not found"}, status=404)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"AI Drama 00-06 测试控制台已启动：{url}")
    print("按 Ctrl+C 停止。")
    if os.getenv("AI_DRAMA_UI_NO_BROWSER", "0") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
