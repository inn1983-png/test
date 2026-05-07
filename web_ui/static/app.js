const state = {
  pipeline: [],
  currentJob: null,
  currentSnapshot: null,
  eventSource: null,
  logLines: [],
  selectedModule: null,
};

const MODULE_NAMES = {
  "00_main_controller": "总控",
  "01_novel_parser": "小说解析",
  "02_script_writer": "剧本改编",
  "03_character_system": "角色库",
  "04_scene_system": "场景库",
  "05_prop_system": "道具库",
  "06_storyboard": "分镜",
  "07_storyboard_image": "分镜图",
  "08_audio": "音频",
  "09_video": "视频",
  "10_final_assembly": "合成",
};

const STAGE_NAMES = {
  "01A": "故事理解", "01B": "段落切分", "01C": "事件图谱", "01D": "候选提取", "01E": "制作预测", "01F": "质量检查",
  "02A": "改编蓝图", "02B": "剧本结构", "02C": "语音行计划", "02D": "剧本草稿", "02E": "制作标注", "02F": "质量检查",
  "03A": "别名归并", "03B": "角色卡", "03C": "剧本绑定", "03D": "质量检查", "03E": "资产复核",
  "04A": "场景归并", "04B": "场景卡", "04C": "剧本绑定", "04D": "质量检查", "04E": "资产复核",
  "05A": "道具归并", "05B": "道具卡", "05C": "剧本绑定", "05D": "质量检查", "05E": "资产复核",
  "06A": "资产门控", "06B": "分镜规划", "06C": "单帧分镜", "06D": "连续性绑定", "06E": "质量检查",
  "07A": "参考资产", "07B": "图片任务", "07C": "ComfyUI", "07D": "图片总检",
  "08A": "音频队列", "08B": "音色绑定", "08C": "TTS执行", "08D": "混音字幕",
  "09A": "输入检查", "09B": "视频规划", "09C": "LTX执行", "09D": "视频总检",
  "10A": "输入检查", "10B": "视频准备", "10C": "音频字幕对齐", "10D": "最终导出",
};

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const escAttr = (v) => esc(v).replace(/'/g, "&#39;");
const mName = (n) => MODULE_NAMES[n] || n || "?";
const sName = (n) => STAGE_NAMES[String(n || "").slice(0, 3)] || n || "?";
const statusText = (s) => ({success:"完成",running:"运行中",failed:"失败",blocked:"阻塞",skipped:"跳过",pending:"等待",queued:"排队",needs_review:"需复核"}[s] || s || "等待");

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function init() {
  bindActions();
  await loadPipeline();
  renderStepRunGrid();
  await refreshAll();
}

function bindActions() {
  $("startFullBtn")?.addEventListener("click", () => startJob({}));
  $("startTextBtn")?.addEventListener("click", () => startJob({ from_module: "01_novel_parser", image_execution_mode: "dry_run", audio_execution_mode: "dry_run", video_execution_mode: "dry_run" }));
  $("dataLinkBtn")?.addEventListener("click", () => startJob({ job_kind: "data_link_check", project_id: $("projectIdInput")?.value || "ui_data_link_check" }, "/api/system/check-data-link"));
  $("selfCheckBtn")?.addEventListener("click", () => startJob({ job_kind: "controller_self_check", project_id: $("projectIdInput")?.value || "self_check_project", keep_self_check: true }, "/api/system/self-check"));
  $("stopBtn")?.addEventListener("click", stopJob);
  $("refreshBtn")?.addEventListener("click", refreshAll);
  $("closePreviewBtn")?.addEventListener("click", () => $("previewModal").classList.add("hidden"));
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
}

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".tab-content").forEach((c) => c.classList.toggle("active", c.id === `tab${tab.charAt(0).toUpperCase() + tab.slice(1)}`));
}

function getPayload(extra) {
  return {
    mode: "project",
    project_id: $("projectIdInput")?.value,
    novel_text: $("novelTextInput")?.value,
    llm_base_url: $("llmBaseUrlInput")?.value,
    llm_model: $("llmModelInput")?.value,
    llm_api_key: $("llmApiKeyInput")?.value,
    image_execution_mode: $("imageModeInput")?.value,
    audio_execution_mode: $("audioModeInput")?.value,
    video_execution_mode: $("videoModeInput")?.value,
    strict_order: true,
    ...extra,
  };
}

async function startJob(extra, endpoint = "/api/jobs/start") {
  const payload = getPayload(extra);
  if (!payload.project_id && !payload.book_id) {
    payload.project_id = "project_" + new Date().toISOString().slice(0, 10).replace(/-/g, "");
  }
  const data = await api(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  state.currentJob = data.job;
  state.logLines = [];
  $("liveLog").innerHTML = "";
  $("stopBtn").disabled = false;
  connectEvents(state.currentJob.id);
  updateTopbar();
}

async function stopJob() {
  if (state.currentJob) await api(`/api/jobs/${state.currentJob.id}/stop`, { method: "POST" });
}

async function loadPipeline() {
  const data = await api("/api/pipeline");
  state.pipeline = Array.isArray(data.pipeline) ? data.pipeline : [];
}

async function refreshAll() {
  await loadProjects();
  if (state.currentJob) {
    const data = await api(`/api/jobs/${state.currentJob.id}/snapshot`);
    state.currentSnapshot = data.snapshot;
    renderPipeline();
    renderStageDetail();
    renderStepRunGrid();
  } else {
    renderPipeline();
    renderStepRunGrid();
  }
}

async function loadProjects() {
  const data = await api("/api/projects");
  const projects = data.projects || [];
  const wrap = $("projectList");
  if (!wrap) return;
  if (!projects.length) { wrap.innerHTML = `<div style="color:var(--muted);font-size:12px">暂无项目</div>`; return; }
  wrap.innerHTML = projects.slice(0, 8).map((p) =>
    `<div class="project-item" onclick="openProject('${escAttr(p.project_id)}')"><div class="pid">${esc(p.project_id)}</div><div class="pstatus">${statusText(p.status)}</div></div>`
  ).join("");
}

function connectEvents(jobId) {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource(`/api/jobs/${jobId}/events`);

  state.eventSource.addEventListener("log", (ev) => {
    const event = JSON.parse(ev.data);
    const line = event.payload.line || "";
    state.logLines.push(line);
    state.logLines = state.logLines.slice(-2000);
    appendLogLine(line);
  });

  state.eventSource.addEventListener("snapshot", (ev) => {
    const event = JSON.parse(ev.data);
    state.currentSnapshot = event.payload;
    renderPipeline();
    renderStageDetail();
    renderStepRunGrid();
  });

  state.eventSource.addEventListener("job_started", () => {
    updateTopbar();
  });

  state.eventSource.addEventListener("job_finished", (ev) => {
    const event = JSON.parse(ev.data);
    if (state.currentJob) {
      state.currentJob.status = event.payload.status;
      state.currentJob.return_code = event.payload.return_code;
    }
    $("stopBtn").disabled = true;
    updateTopbar();
    refreshAll();
  });

  state.eventSource.addEventListener("job_error", (ev) => {
    const event = JSON.parse(ev.data);
    appendLogLine(`[ERROR] ${event.payload.error}`);
  });
}

function classifyLog(line) {
  if (!line) return "";
  const l = line.toLowerCase();
  if (l.includes("[error]") || l.includes("traceback") || l.includes("runtimeerror") || l.includes("exception")) return "log-error";
  if (l.includes("[resume]") || l.includes("skipped (cached")) return "log-resume";
  if (l.match(/\[\d{2}[A-F]\]/) || l.match(/\[\d{2}[A-F]_/) || l.includes("[stage_start]") || l.includes("[stage_end]")) return "log-stage";
  if (l.includes("[run]") && l.match(/\d{2}_/)) return "log-stage";
  if (l.includes("success") || l.includes("passed") || l.includes("completed") || l.includes("[done]")) return "log-success";
  if (l.includes("warn") || l.includes("retry") || l.includes("needs_review")) return "log-warn";
  if (l.includes("llm") || l.includes("json") || l.includes("trace") || l.includes("repair") || l.includes("[llm_json]")) return "log-llm";
  if (l.includes("[run]") || l.includes("[start]") || l.includes("[snapshot]")) return "log-stage";
  if (l.includes("failed") && !l.includes("[error]")) return "log-error";
  return "";
}

function appendLogLine(line) {
  const box = $("liveLog");
  if (!box) return;
  const cls = classifyLog(line);
  const div = document.createElement("div");
  div.className = `log-line ${cls}`;
  div.textContent = line;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function updateTopbar() {
  const dot = $("jobStatusBadge");
  const text = $("jobStatusText");
  if (!state.currentJob) { dot.className = "status-dot"; text.textContent = "空闲"; return; }
  const s = state.currentJob.status || "queued";
  dot.className = `status-dot ${s}`;
  text.textContent = `${state.currentJob.id} · ${statusText(s)}`;
}

function renderPipeline() {
  const flow = $("pipelineFlow");
  if (!flow) return;
  const modules = state.currentSnapshot?.modules || [];
  const moduleMap = {};
  for (const m of modules) moduleMap[m.name] = m;

  const allModules = ["00_main_controller", ...state.pipeline];
  flow.innerHTML = allModules.map((name, i) => {
    const m = moduleMap[name] || { name, status: "pending", stages: [], current_stage: {} };
    const stages = m.stages || [];
    const currentStage = m.current_stage || {};
    const currentStageId = currentStage.current_stage_id || "";

    let stageBar = "";
    if (stages.length) {
      const stageItems = stages.map((s) => {
        const sid = s.stage_id || s.name || "";
        const sidShort = String(sid).slice(0, 3);
        const isCurrent = sidShort === String(currentStageId).slice(0, 3);
        const dotCls = isCurrent ? "running" : s.passed === true ? "passed" : s.passed === false ? "failed" : "pending";
        const label = sName(sid);
        return `<div class="si ${dotCls}" title="${esc(sid)} ${esc(label)}"><span class="si-dot"></span><span class="si-label">${esc(sidShort)}</span></div>`;
      }).join("");
      stageBar = `<div class="stage-bar">${stageItems}</div>`;
    }

    const currentLabel = currentStageId ? `${currentStageId} ${sName(currentStageId)}` : "";
    const arrow = i < allModules.length - 1 ? `<span class="module-arrow">→</span>` : "";
    return `<div class="module-node status-${m.status || 'pending'}" onclick="selectModule('${escAttr(name)}')"><div class="mn-id">${name.slice(0, 2)}</div><div class="mn-name">${mName(name)}</div><div class="mn-status">${statusText(m.status)}</div>${currentLabel ? `<div class="mn-current">${esc(currentLabel)}</div>` : ""}${stageBar}</div>${arrow}`;
  }).join("");
}

function selectModule(name) {
  state.selectedModule = name;
  renderStageDetail();
  switchTab("stage");
}

async function renderStageDetail() {
  const wrap = $("stageDetail");
  if (!wrap) return;
  if (!state.selectedModule || !state.currentSnapshot) {
    wrap.innerHTML = `<div style="color:var(--muted);padding:20px">点击上方模块查看阶段详情</div>`;
    return;
  }
  const modules = state.currentSnapshot.modules || [];
  const m = modules.find((mod) => mod.name === state.selectedModule);
  if (!m) { wrap.innerHTML = `<div style="color:var(--muted)">无数据</div>`; return; }

  const stages = m.stages || [];
  if (!stages.length) {
    wrap.innerHTML = `<div class="stage-detail-card"><h3>${esc(mName(m.name))}</h3><div style="color:var(--muted)">暂无阶段输出</div></div>`;
    return;
  }

  wrap.innerHTML = stages.map((s) => {
    const sid = s.stage_id || s.name || "";
    const score = s.score ?? "-";
    const scoreCls = typeof s.score === "number" ? (s.score >= 80 ? "score-high" : s.score < 60 ? "score-low" : "") : "";
    const passed = s.passed === true ? "✓ 通过" : s.passed === false ? "✗ 未通过" : "待定";
    const issues = s.issues_count ?? 0;
    return `<div class="stage-detail-card">
      <h3>${esc(sName(sid))} <span style="color:var(--muted);font-weight:400;font-size:12px">${esc(sid)}</span></h3>
      <div class="sdc-meta">
        <div class="sdc-meta-item"><div class="label">评分</div><div class="value ${scoreCls}">${score}</div></div>
        <div class="sdc-meta-item"><div class="label">通过</div><div class="value">${passed}</div></div>
        <div class="sdc-meta-item"><div class="label">问题数</div><div class="value">${issues}</div></div>
        <div class="sdc-meta-item"><div class="label">文件</div><div class="value" style="font-size:11px;word-break:break-all">${esc(s.name || "-")}</div></div>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="btn small" onclick="previewFile('${escAttr(s.path)}')">查看输出</button>
        ${s.llm_trace_request_path ? `<button class="btn small ghost" onclick="previewFile('${escAttr(s.llm_trace_request_path)}')">LLM trace</button>` : ""}
        ${s.llm_trace_dir ? `<button class="btn small ghost" onclick="previewTraceDir('${escAttr(s.llm_trace_dir)}')">查看完整 trace</button>` : ""}
      </div>
    </div>`;
  }).join("");
}

async function openProject(projectId) {
  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/snapshot`);
  state.currentSnapshot = data.snapshot;
  state.currentJob = null;
  state.selectedModule = null;
  renderPipeline();
  renderStageDetail();
  updateTopbar();
}

async function previewFile(path) {
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    $("previewTitle").textContent = data.path || path;
    if (data.type === "json") {
      $("previewContent").textContent = JSON.stringify(data.content, null, 2);
    } else if (data.type === "image") {
      $("previewContent").innerHTML = `<img src="${data.url}" style="max-width:100%;border-radius:12px" />`;
    } else if (data.type === "media") {
      $("previewContent").textContent = `媒体文件：${data.path}\n大小：${data.size || 0} bytes`;
    } else {
      $("previewContent").textContent = data.content || `二进制文件 ${data.size || 0} bytes`;
    }
    $("previewModal").classList.remove("hidden");
  } catch (err) {
    $("previewTitle").textContent = "预览失败";
    $("previewContent").textContent = String(err);
    $("previewModal").classList.remove("hidden");
  }
}

async function previewTraceDir(dirPath) {
  try {
    const relDir = dirPath.replace(/\\/g, "/");
    const parts = relDir.split("/");
    const requestPath = relDir + "/request.json";
    const responsePath = relDir + "/response.json";
    const reqData = await api(`/api/file?path=${encodeURIComponent(requestPath)}`);
    const resData = await api(`/api/file?path=${encodeURIComponent(responsePath)}`);
    let content = "=== REQUEST ===\n";
    if (reqData.type === "json") content += JSON.stringify(reqData.content, null, 2);
    else content += reqData.content || "(empty)";
    content += "\n\n=== RESPONSE ===\n";
    if (resData.type === "json") content += JSON.stringify(resData.content, null, 2);
    else content += resData.content || "(empty)";
    $("previewTitle").textContent = `LLM Trace: ${parts.slice(-2).join("/")}`;
    $("previewContent").textContent = content;
    $("previewModal").classList.remove("hidden");
  } catch (err) {
    $("previewTitle").textContent = "Trace 预览失败";
    $("previewContent").textContent = String(err);
    $("previewModal").classList.remove("hidden");
  }
}

window.openProject = openProject;
window.selectModule = selectModule;
window.previewFile = previewFile;
window.previewTraceDir = previewTraceDir;
window.getPayload = getPayload;
window.runSingleModule = runSingleModule;

function renderStepRunGrid() {
  const grid = $("stepRunGrid");
  if (!grid) return;
  const modules = state.pipeline.length ? state.pipeline : [
    "01_novel_parser", "02_script_writer", "03_character_system",
    "04_scene_system", "05_prop_system", "06_storyboard",
    "07_storyboard_image", "08_audio", "09_video", "10_final_assembly",
  ];
  const moduleStatusMap = {};
  if (state.currentSnapshot?.modules) {
    for (const m of state.currentSnapshot.modules) {
      moduleStatusMap[m.name] = m.status || "pending";
    }
  }
  grid.innerHTML = modules.map((name) => {
    const s = moduleStatusMap[name] || "pending";
    const cls = s === "success" ? "step-success" : s === "running" ? "step-running" : s === "failed" || s === "blocked" ? "step-failed" : "";
    return `<button class="step-btn ${cls}" onclick="runSingleModule('${escAttr(name)}')"><span class="step-id">${name.slice(0, 2)}</span><span class="step-name">${mName(name)}</span><span class="step-status">${statusText(s)}</span></button>`;
  }).join("");
}

async function runSingleModule(moduleName) {
  const payload = getPayload({ only_module: moduleName });
  if (!payload.project_id) {
    payload.project_id = "project_" + new Date().toISOString().slice(0, 10).replace(/-/g, "");
  }
  await startJob({ only_module: moduleName });
}

init().catch((err) => { console.error(err); if ($("liveLog")) $("liveLog").textContent = String(err); });
