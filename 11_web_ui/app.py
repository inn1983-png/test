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

ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = int(os.getenv("AI_DRAMA_UI_PORT", "1144"))
MODULES = ["01_novel_parser", "02_script_writer", "03_character_system", "04_scene_system", "05_prop_system", "06_storyboard"]
OUTPUTS = {
    "01_novel_parser": ["novel_analysis.json", "novel_meta.json"],
    "02_script_writer": ["script.json", "script.txt", "script_meta.json"],
    "03_character_system": ["characters.json", "characters_meta.json"],
    "04_scene_system": ["scenes.json", "scenes_meta.json"],
    "05_prop_system": ["props.json", "props_meta.json"],
    "06_storyboard": ["storyboard.json", "storyboard_meta.json"],
}
STATE_LOCK = threading.Lock()
STATE: dict[str, Any] = {"running": False, "task": "", "code": None, "logs": [], "cmd": []}


def project_dir(pid: str) -> Path:
    return ROOT / "workspace" / "projects" / pid


def novel_file(pid: str) -> Path:
    return project_dir(pid) / "input" / "novel.txt"


def clean_pid(value: str) -> str:
    s = "".join(c for c in value.strip() if c.isalnum() or c in "_-." )
    return s or "project_test_001"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except Exception:
        return {}


def log(line: str) -> None:
    with STATE_LOCK:
        STATE["logs"].append(line.rstrip())
        STATE["logs"] = STATE["logs"][-1000:]


def state() -> dict[str, Any]:
    with STATE_LOCK:
        s = dict(STATE)
        s["logs"] = list(STATE["logs"])
        return s


def run_cmd(args: list[str], task: str) -> None:
    with STATE_LOCK:
        STATE.update({"running": True, "task": task, "code": None, "logs": [], "cmd": args})
    log("开始：" + task)
    log("工作目录：" + str(ROOT))
    log("命令：" + " ".join(args))
    try:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        p = subprocess.Popen(args, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
        assert p.stdout is not None
        for line in p.stdout:
            log(line)
        code = p.wait()
        log(f"结束：returncode={code}")
        with STATE_LOCK:
            STATE["code"] = code
    except Exception as exc:
        log("运行失败：" + repr(exc))
        with STATE_LOCK:
            STATE["code"] = -1
    finally:
        with STATE_LOCK:
            STATE["running"] = False


def start(args: list[str], task: str) -> bool:
    with STATE_LOCK:
        if STATE["running"]:
            return False
    threading.Thread(target=run_cmd, args=(args, task), daemon=True).start()
    return True


def file_info(path: Path) -> dict[str, Any]:
    info = {"exists": path.exists(), "path": str(path.relative_to(ROOT)) if path.exists() else str(path.relative_to(ROOT))}
    if path.exists():
        info["size"] = path.stat().st_size
    return info


def input_info(pid: str) -> dict[str, Any]:
    path = novel_file(pid)
    text = read_text(path)
    info = file_info(path)
    info.update({"chars": len(text), "non_empty": bool(text.strip()), "preview": text[:300]})
    return info


def module_status(pid: str, module: str) -> dict[str, Any]:
    base = project_dir(pid) / module
    outputs = []
    status = "not_run"
    for fn in OUTPUTS[module]:
        p = base / fn
        row = file_info(p)
        row["file"] = fn
        if p.exists():
            status = "done"
            if fn.endswith(".json"):
                data = read_json(p)
                row["json_status"] = data.get("status")
                row["schema_passed"] = (data.get("schema_validation") or {}).get("passed")
                row["needs_review"] = (data.get("quality_report") or {}).get("needs_review")
                if row.get("json_status") == "needs_review" or row.get("needs_review"):
                    status = "needs_review"
        outputs.append(row)
    return {"module": module, "status": status, "outputs": outputs}


def short(value: Any, n: int = 80) -> str:
    s = "" if value is None else str(value)
    return s if len(s) <= n else s[:n] + "..."


def summarize(pid: str, module: str) -> dict[str, Any]:
    base = project_dir(pid) / module
    if module == "01_novel_parser":
        d = read_json(base / "novel_analysis.json")
        return {"title": "01 小说解析摘要", "items": [
            {"名称": "状态", "内容": d.get("status", "")},
            {"名称": "候选角色数", "内容": len(d.get("candidate_characters", []) or [])},
            {"名称": "候选场景数", "内容": len(d.get("candidate_scenes", []) or [])},
            {"名称": "候选道具数", "内容": len(d.get("candidate_props", []) or [])},
            {"名称": "故事主轴", "内容": short(d.get("story_spine", {}), 220)},
        ]}
    if module == "02_script_writer":
        d = read_json(base / "script.json")
        return {"title": "02 剧本摘要", "script_text": d.get("script_text", ""), "items": [
            {"名称": "状态", "内容": d.get("status", "")},
            {"名称": "剧本段数", "内容": len(d.get("segments", []) or [])},
            {"名称": "语音行数", "内容": len(d.get("voice_line_plan", []) or [])},
            {"名称": "外观变化数", "内容": len(d.get("appearance_state_changes", []) or [])},
        ]}
    if module == "03_character_system":
        d = read_json(base / "characters.json")
        rows = [{"角色": x.get("canonical_name"), "等级": x.get("asset_level"), "默认服装": x.get("default_costume_id"), "服装数": len(x.get("costume_variants", []) or [])} for x in d.get("characters", []) or [] if isinstance(x, dict)]
        return {"title": "03 角色库摘要", "table": rows, "items": [{"名称": "状态", "内容": d.get("status", "")}, {"名称": "角色数", "内容": len(rows)}]}
    if module == "04_scene_system":
        d = read_json(base / "scenes.json")
        rows = [{"场景": x.get("canonical_scene_name"), "等级": x.get("asset_level"), "父场景": x.get("parent_scene", "")} for x in d.get("scenes", []) or [] if isinstance(x, dict)]
        return {"title": "04 场景库摘要", "table": rows, "items": [{"名称": "状态", "内容": d.get("status", "")}, {"名称": "场景数", "内容": len(rows)}]}
    if module == "05_prop_system":
        d = read_json(base / "props.json")
        rows = [{"道具": x.get("canonical_prop_name"), "等级": x.get("asset_level"), "穿戴策略": x.get("wearable_policy", "")} for x in d.get("props", []) or [] if isinstance(x, dict)]
        return {"title": "05 道具库摘要", "table": rows, "items": [{"名称": "状态", "内容": d.get("status", "")}, {"名称": "道具数", "内容": len(rows)}]}
    if module == "06_storyboard":
        d = read_json(base / "storyboard.json")
        rows = []
        for x in d.get("frames", []) or []:
            if not isinstance(x, dict):
                continue
            chars = ", ".join([c.get("canonical_name", "") for c in x.get("characters", []) if isinstance(c, dict)])
            scene = (x.get("scene") or {}).get("canonical_scene_name", "") if isinstance(x.get("scene"), dict) else ""
            rows.append({"序号": x.get("sequence_index"), "帧": x.get("frame_id"), "场景": scene, "角色": chars, "动作": short(x.get("story_action", ""), 80)})
        return {"title": "06 单帧分镜摘要", "table": rows, "items": [{"名称": "状态", "内容": d.get("status", "")}, {"名称": "分镜帧数", "内容": len(rows)}, {"名称": "造型需求数", "内容": len(d.get("appearance_asset_requirements", []) or [])}]}
    return {"title": module, "items": []}


def raw_output(pid: str, module: str, fn: str) -> dict[str, Any]:
    if module not in OUTPUTS or fn not in OUTPUTS[module]:
        return {"error": "不允许读取该文件"}
    p = project_dir(pid) / module / fn
    if not p.exists():
        return {"error": "文件不存在", "path": str(p.relative_to(ROOT))}
    text = read_text(p)
    return {"path": str(p.relative_to(ROOT)), "text": text, "json": read_json(p) if fn.endswith(".json") else None}


def send_json(h: BaseHTTPRequestHandler, data: Any, code: int = 200) -> None:
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    h.send_response(code); h.send_header("Content-Type", "application/json; charset=utf-8"); h.send_header("Content-Length", str(len(raw))); h.end_headers(); h.wfile.write(raw)


def send_html(h: BaseHTTPRequestHandler) -> None:
    raw = HTML.encode("utf-8")
    h.send_response(200); h.send_header("Content-Type", "text/html; charset=utf-8"); h.send_header("Content-Length", str(len(raw))); h.end_headers(); h.wfile.write(raw)


def body(h: BaseHTTPRequestHandler) -> dict[str, Any]:
    n = int(h.headers.get("Content-Length", "0") or 0)
    if not n: return {}
    try: return json.loads(h.rfile.read(n).decode("utf-8"))
    except Exception: return {}


HTML = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>00-06控制台</title><style>
body{margin:0;background:#0b1220;color:#e5e7eb;font-family:system-ui,"Segoe UI",sans-serif}header{padding:18px 24px;background:#111827}main{padding:18px;display:grid;gap:14px}.card{background:#0f172a;border:1px solid #334155;border-radius:14px;padding:16px}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}input,textarea,select{background:#020617;color:#e5e7eb;border:1px solid #475569;border-radius:8px;padding:9px}button{background:#2563eb;color:#fff;border:0;border-radius:8px;padding:9px 12px;font-weight:700}button.secondary{background:#475569}button:disabled{opacity:.45}.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}.mod{background:#020617;border:1px solid #334155;border-radius:10px;padding:10px;cursor:pointer}.badge{padding:2px 7px;border-radius:99px;background:#64748b;color:#020617;font-size:12px}.done{background:#22c55e}.needs_review{background:#f59e0b}.not_run{background:#94a3b8}pre{background:#020617;border:1px solid #334155;border-radius:10px;padding:12px;white-space:pre-wrap;max-height:520px;overflow:auto}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #334155;padding:7px;text-align:left}.note{color:#94a3b8;font-size:13px}.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:900px){.grid,.cols{grid-template-columns:1fr}}
</style></head><body><header><h1>00–06 Pipeline 测试控制台</h1><div class="note">用于运行 Pipeline、查看摘要、查看原始 JSON/TXT。端口 1144。</div></header><main>
<div class="card"><h2>项目</h2><div class="row"><input id="pid" value="project_test_001"><button onclick="refresh()">刷新</button><button onclick="saveInput()">保存输入框到 novel.txt</button><button onclick="loadInput()" class="secondary">读取 novel.txt</button></div><p id="inputInfo" class="note"></p><textarea id="novel" style="width:100%;height:100px" placeholder="可选：粘贴小说后保存。你也可以手动放入 novel.txt。"></textarea></div>
<div class="card"><h2>运行</h2><div class="row"><button onclick="run('validate')" class="secondary">校验 pipeline</button><button onclick="run('all')">运行 01–06</button><select id="modSel"></select><button onclick="run('module')" class="secondary">运行选中模块</button></div><p id="runState" class="note"></p><pre id="logs">等待运行...</pre></div>
<div class="card"><h2>模块状态（点击模块看摘要）</h2><div id="mods" class="grid"></div></div>
<div class="cols"><div class="card"><h2>结果摘要</h2><div id="summary">点击上面的模块查看。</div></div><div class="card"><h2>原始输出</h2><div class="row"><select id="rawMod" onchange="fillFiles()"></select><select id="rawFile"></select><button onclick="loadRaw()">查看原始文件</button></div><pre id="raw">等待选择文件...</pre></div></div>
</main><script>
const modules=['01_novel_parser','02_script_writer','03_character_system','04_scene_system','05_prop_system','06_storyboard'];
const files={'01_novel_parser':['novel_analysis.json','novel_meta.json'],'02_script_writer':['script.json','script.txt','script_meta.json'],'03_character_system':['characters.json','characters_meta.json'],'04_scene_system':['scenes.json','scenes_meta.json'],'05_prop_system':['props.json','props_meta.json'],'06_storyboard':['storyboard.json','storyboard_meta.json']};
function pid(){return document.getElementById('pid').value||'project_test_001'}
async function api(u,o){let r=await fetch(u,o);return await r.json()}
function init(){let a=document.getElementById('modSel'),b=document.getElementById('rawMod');modules.forEach(m=>{a.innerHTML+=`<option>${m}</option>`;b.innerHTML+=`<option>${m}</option>`});fillFiles();refresh();setInterval(refresh,2000)}
function fillFiles(){let m=document.getElementById('rawMod').value;document.getElementById('rawFile').innerHTML=files[m].map(f=>`<option>${f}</option>`).join('')}
async function refresh(){let d=await api('/api/status?project_id='+encodeURIComponent(pid()));document.getElementById('inputInfo').textContent=`输入文件：${d.input.path}｜存在：${d.input.exists}｜大小：${d.input.size}｜字符：${d.input.chars}`;document.getElementById('runState').textContent=`状态：${d.state.running?'运行中':'空闲'}｜任务：${d.state.task||'-'}｜返回码：${d.state.code??'-'}`;document.getElementById('logs').textContent=(d.state.logs||[]).join('\n')||'等待运行...';document.getElementById('mods').innerHTML=d.modules.map(x=>`<div class="mod" onclick="showSummary('${x.module}')"><b>${x.module}</b><br><span class="badge ${x.status}">${x.status}</span><div class="note">${x.outputs.map(o=>(o.exists?'✅ ':'— ')+o.file).join('<br>')}</div></div>`).join('')}
async function saveInput(){let d=await api('/api/save_input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:pid(),text:document.getElementById('novel').value})});alert(d.ok?'已保存':'失败：'+d.error);refresh()}
async function loadInput(){let d=await api('/api/input?project_id='+encodeURIComponent(pid()));document.getElementById('novel').value=d.text||''}
async function run(kind){let body={project_id:pid(),module:document.getElementById('modSel').value};let d=await api('/api/run_'+kind,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!d.ok)alert(d.error||'启动失败');refresh()}
async function showSummary(m){let d=await api('/api/summary?project_id='+encodeURIComponent(pid())+'&module='+encodeURIComponent(m));let h=`<h3>${d.title}</h3>`;(d.items||[]).forEach(i=>h+=`<p><b>${i['名称']}：</b>${i['内容']}</p>`);if(d.script_text)h+=`<h4>剧本文本</h4><pre>${esc(d.script_text)}</pre>`;if(d.table){h+='<table><tr>'+Object.keys(d.table[0]||{}).map(k=>`<th>${k}</th>`).join('')+'</tr>'+d.table.map(r=>'<tr>'+Object.values(r).map(v=>`<td>${esc(String(v??''))}</td>`).join('')+'</tr>').join('')+'</table>'}document.getElementById('summary').innerHTML=h}
async function loadRaw(){let m=document.getElementById('rawMod').value,f=document.getElementById('rawFile').value;let d=await api(`/api/raw?project_id=${encodeURIComponent(pid())}&module=${encodeURIComponent(m)}&file=${encodeURIComponent(f)}`);document.getElementById('raw').textContent=d.error?d.error+'\n'+(d.path||''):(d.json?JSON.stringify(d.json,null,2):d.text)}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
init();</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        q = urlparse(self.path)
        qs = parse_qs(q.query)
        pid = clean_pid(qs.get("project_id", ["project_test_001"])[0])
        if q.path == "/": send_html(self); return
        if q.path == "/api/status": send_json(self, {"input": input_info(pid), "modules": [module_status(pid, m) for m in MODULES], "state": state()}); return
        if q.path == "/api/input": send_json(self, {"text": read_text(novel_file(pid))}); return
        if q.path == "/api/summary": send_json(self, summarize(pid, qs.get("module", [""])[0])); return
        if q.path == "/api/raw": send_json(self, raw_output(pid, qs.get("module", [""])[0], qs.get("file", [""])[0])); return
        send_json(self, {"error": "not found"}, 404)

    def do_POST(self) -> None:
        q = urlparse(self.path)
        b = body(self)
        pid = clean_pid(str(b.get("project_id", "project_test_001")))
        if q.path == "/api/save_input":
            text = str(b.get("text", ""))
            if not text.strip(): send_json(self, {"ok": False, "error": "输入框为空"}, 400); return
            p = novel_file(pid); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
            send_json(self, {"ok": True, "path": str(p.relative_to(ROOT))}); return
        if q.path == "/api/run_validate":
            send_json(self, {"ok": start([sys.executable, "00_main_controller/validate_pipeline.py", "--pipeline", "pipeline.json", "--strict-order"], "校验 pipeline")}); return
        if q.path == "/api/run_all":
            args = [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", pid, "--from-module", "01_novel_parser", "--to-module", "06_storyboard"]
            send_json(self, {"ok": start(args, "运行 01–06")}); return
        if q.path == "/api/run_module":
            m = str(b.get("module", ""))
            if m not in MODULES: send_json(self, {"ok": False, "error": "模块不允许"}, 400); return
            args = [sys.executable, "00_main_controller/run_pipeline.py", "--mode", "project", "--project-id", pid, "--only-module", m]
            send_json(self, {"ok": start(args, "运行 " + m)}); return
        send_json(self, {"error": "not found"}, 404)


def main() -> int:
    url = f"http://{HOST}:{PORT}"
    print("AI Drama 00-06 控制台：" + url)
    if os.getenv("AI_DRAMA_UI_NO_BROWSER", "0") != "1": threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
