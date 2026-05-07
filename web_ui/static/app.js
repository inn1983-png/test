const state = {
  pipeline: [],
  displayPipeline: [],
  currentJob: null,
  currentSnapshot: null,
  eventSource: null,
  logLines: [],
};

const MODULE_DISPLAY_NAMES = {
  "00_main_controller": "00 总控 / 自检",
  "01_novel_parser": "01 小说解析",
  "02_script_writer": "02 剧本改编",
  "03_character_system": "03 角色资产库",
  "04_scene_system": "04 场景资产库",
  "05_prop_system": "05 道具资产库",
  "06_storyboard": "06 单帧分镜",
  "07_storyboard_image": "07 分镜图片",
  "08_audio": "08 音频生成",
  "09_video": "09 视频生成",
  "10_final_assembly": "10 最终合成",
};

const STAGE_DISPLAY_NAMES = {
  "01A": "01A 原文结构解析", "01B": "01B 候选角色/场景/道具提取", "01C": "01C 故事理解与冲突梳理", "01D": "01D 视觉风险与高留存片段", "01E": "01E 小说解析总检",
  "02A": "02A 剧情拆解", "02B": "02B 剧本初稿", "02C": "02C 对白/OS/留白优化", "02D": "02D 视觉动作链绑定", "02E": "02E 剧本总检与外观变化",
  "03A": "03A 角色归并计划", "03B": "03B 角色资产卡", "03C": "03C 剧本使用绑定", "03D": "03D 角色库总检", "03E": "03E 面向分镜复核",
  "04A": "04A 场景归并计划", "04B": "04B 场景资产卡", "04C": "04C 剧本使用绑定", "04D": "04D 场景库总检", "04E": "04E 面向分镜复核",
  "05A": "05A 道具归并计划", "05B": "05B 道具资产卡", "05C": "05C 剧本使用绑定", "05D": "05D 道具库总检", "05E": "05E 面向分镜复核",
  "06A": "06A 资产闸门检查", "06B": "06B 分镜规划", "06C": "06C 单帧分镜生成", "06D": "06D 连续性绑定", "06E": "06E 分镜总检",
  "07A": "07A 参考资产准备", "07B": "07B 分镜图片任务", "07C": "07C ComfyUI 执行", "07D": "07D 图片总检",
  "08A": "08A 音频队列", "08B": "08B 音色情绪绑定", "08C": "08C TTS 执行", "08D": "08D 混音字幕",
  "09A": "09A 输入检查", "09B": "09B 视频任务规划", "09C": "09C LTX 执行", "09D": "09D 视频总检",
  "10A": "10A 输入检查", "10B": "10B 视频准备", "10C": "10C 音频字幕对齐", "10D": "10D 最终导出",
};

const $ = (id) => document.getElementById(id);
const moduleName = (name) => MODULE_DISPLAY_NAMES[name] || name || "未知模块";
const stageName = (name) => STAGE_DISPLAY_NAMES[String(name || "").slice(0, 3)] || name || "未命名阶段";

function statusLabel(status) {
  const map = { success: "完成", running: "运行中", failed: "失败", blocked: "阻塞", skipped: "跳过", pending: "等待", queued: "排队", not_started: "未开始", needs_review: "需复核", stopping: "停止中", archived: "已归档", pass: "通过", warn: "警告", fail: "失败" };
  return map[status] || status || "未知";
}
function badge(status) { const cls = String(status || "pending").replace(/[^a-zA-Z0-9_-]/g, ""); return `<span class="badge ${cls}">${statusLabel(status)}</span>`; }
async function api(path, options = {}) { const res = await fetch(path, options); if (!res.ok) throw new Error(await res.text()); return res.json(); }

async function init() { bindNav(); bindActions(); await loadPipeline(); await refreshAll(); }

function bindNav() {
  document.querySelectorAll(".nav-item").forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.view)));
  document.querySelectorAll("[data-jump]").forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.jump)));
}
function switchView(view) { document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view)); document.querySelectorAll(".view").forEach((item) => item.classList.remove("active")); const target = $(`view-${view}`); if (target) target.classList.add("active"); }

function bindActions() {
  $("refreshBtn")?.addEventListener("click", refreshAll);
  $("startBtn")?.addEventListener("click", () => startJob({}));
  $("startTextPhaseBtn")?.addEventListener("click", () => startJob({ from_module: "01_novel_parser", image_execution_mode: "dry_run", audio_execution_mode: "dry_run", video_execution_mode: "dry_run" }));
  $("startImagePhaseBtn")?.addEventListener("click", () => startJob({ only_module: "07_storyboard_image", image_execution_mode: $("imageExecutionModeInput")?.value || "dry_run" }));
  $("dataLinkCheckBtn")?.addEventListener("click", () => startJob({ job_kind: "data_link_check", project_id: $("projectIdInput")?.value || "ui_data_link_check" }, "/api/system/check-data-link"));
  $("controllerSelfCheckBtn")?.addEventListener("click", () => startJob({ job_kind: "controller_self_check", project_id: $("projectIdInput")?.value || "self_check_project", keep_self_check: true }, "/api/system/self-check"));
  $("dryRunBtn")?.addEventListener("click", () => startJob({ dry_run: true, project_id: $("projectIdInput")?.value || "ui_dry_run_check" }));
  $("emptyContextBtn")?.addEventListener("click", () => startJob({ empty_pipeline: true, project_id: $("projectIdInput")?.value || "ui_empty_context" }));
  $("stopBtn")?.addEventListener("click", stopCurrentJob);
  $("closePreviewBtn")?.addEventListener("click", () => $("previewModal").classList.add("hidden"));
  $("previewStoryboardBtn")?.addEventListener("click", () => { const rel = currentRunDir(); if (rel) previewFile(`${rel}/06_storyboard/storyboard.json`); });
  $("previewImageManifestBtn")?.addEventListener("click", () => { const rel = currentRunDir(); if (rel) previewFile(`${rel}/07_storyboard_image/image_manifest.json`); });
  $("previewDependencyBtn")?.addEventListener("click", () => { const rel = currentRunDir(); if (rel) previewFile(`${rel}/07_storyboard_image/dependency_index.json`); });
  document.querySelectorAll(".preview-main-output").forEach((btn) => btn.addEventListener("click", () => { const panel = btn.closest(".asset-panel"); const rel = currentRunDir(); if (rel && panel) previewFile(`${rel}/${panel.dataset.output}`); }));
}

async function loadPipeline() {
  const data = await api("/api/pipeline");
  state.pipeline = Array.isArray(data.pipeline) ? data.pipeline : [];
  state.displayPipeline = Array.isArray(data.display_pipeline) ? data.display_pipeline : ["00_main_controller", ...state.pipeline];
  $("metricModules").textContent = state.displayPipeline.length;
  fillModuleSelects();
  renderTimeline();
}
function fillModuleSelects() {
  const from = $("fromModuleInput"), only = $("onlyModuleInput");
  if (from) from.innerHTML = `<option value="">从头开始</option>` + state.pipeline.map((m) => `<option value="${m}">${moduleName(m)}</option>`).join("");
  if (only) only.innerHTML = `<option value="">不限制</option>` + state.pipeline.map((m) => `<option value="${m}">${moduleName(m)}</option>`).join("");
}

async function refreshAll() {
  await loadProjects();
  if (state.currentJob) { const data = await api(`/api/jobs/${state.currentJob.id}/snapshot`); state.currentSnapshot = data.snapshot; await renderSnapshot(); }
  else { renderTimeline(); renderRetryCenter([]); renderStoryboardWorkspace(null); renderAssetCardGrid(null); }
}
async function loadProjects() {
  const data = await api("/api/projects");
  const projects = data.projects || [], wrap = $("projectList");
  if (!wrap) return;
  if (!projects.length) { wrap.innerHTML = `<div class="muted">暂无项目。可以先点“00–10 数据链路检查”。</div>`; return; }
  wrap.innerHTML = projects.slice(0, 12).map((p) => {
    const suggestion = ["failed", "blocked"].includes(p.status) ? `<div class="muted">有失败/阻塞记录，建议从失败处继续。</div>` : "";
    return `<div class="list-item"><div><strong>${escapeHtml(p.project_id)}</strong><div class="muted">${escapeHtml(p.run_dir)}</div>${p.data_link_check?.total ? `<div class="muted">链路检查：通过 ${p.data_link_check.passed}/${p.data_link_check.total}，失败 ${p.data_link_check.failed}</div>` : ""}${suggestion}<div class="card-actions"><button class="btn small primary" onclick="openProject('${escapeAttr(p.project_id)}')">打开项目</button><button class="btn small" onclick="continueProject('${escapeAttr(p.project_id)}')">从失败处继续</button><button class="btn small" onclick="rerunProjectFromStart('${escapeAttr(p.project_id)}')">从 01 重跑</button><button class="btn small ghost" onclick="archiveProject('${escapeAttr(p.project_id)}')">归档项目</button></div></div><div>${badge(p.status)}</div></div>`;
  }).join("");
}

function getPayload(extra) {
  const payload = {
    mode: $("modeInput")?.value || "project",
    project_id: $("projectIdInput")?.value,
    book_id: $("bookIdInput")?.value,
    chapter_id: $("chapterIdInput")?.value,
    from_module: $("fromModuleInput")?.value,
    only_module: $("onlyModuleInput")?.value,
    novel_text: $("novelTextInput")?.value,
    llm_api_key: $("llmApiKeyInput")?.value,
    llm_base_url: $("llmBaseUrlInput")?.value,
    llm_model: $("llmModelInput")?.value,
    llm_max_tokens: $("llmMaxTokensInput")?.value,
    llm_input_compact: $("llmInputCompactInput")?.value,
    llm_temperature: $("llmTemperatureInput")?.value,
    llm_timeout_sec: $("llmTimeoutInput")?.value,
    image_execution_mode: $("imageExecutionModeInput")?.value,
    comfyui_base_url: $("comfyuiBaseUrlInput")?.value,
    comfyui_workflow_mapping: $("workflowMappingInput")?.value,
    image_style_suffix: $("imageStyleSuffixInput")?.value,
    image_negative_prompt: $("imageNegativePromptInput")?.value,
    audio_execution_mode: $("audioExecutionModeInput")?.value,
    index_tts_root: $("indexTtsRootInput")?.value,
    video_execution_mode: $("videoExecutionModeInput")?.value,
    ffmpeg_bin: $("ffmpegBinInput")?.value,
    strict_order: $("strictOrderInput")?.checked ?? true,
    skip_validation: $("skipValidationInput")?.checked ?? false,
    skip_dependency_check: $("skipDependencyInput")?.checked ?? false,
    ...extra,
  };
  if (payload.only_module) payload.from_module = "";
  return payload;
}

function safeSegment(value) { return String(value || "").trim().replace(/[^a-zA-Z0-9_-]/g, "_").replace(/^_+|_+$/g, ""); }
function targetRunDirForPayload(payload) {
  if (payload.mode === "book_chapter" && safeSegment(payload.book_id) && safeSegment(payload.chapter_id)) return `workspace/books/${safeSegment(payload.book_id)}/chapters/${safeSegment(payload.chapter_id)}`;
  if (safeSegment(payload.project_id)) return `workspace/projects/${safeSegment(payload.project_id)}`;
  return currentRunDir();
}
function formatRequirePath(item) { return `${item?.module || "上游模块"}/${item?.name || "未知产物"}`; }
function requirementSummary(payload, data) {
  const missing = (data.missing_requires || []).map(formatRequirePath);
  const first = missing[0] || "上游关键产物";
  return `${moduleName(payload.only_module)} 缺少 ${first}，建议先从 ${moduleName(data.recommended_from_module)} 开始运行。`;
}
function ensureRequirementModal() {
  let modal = $("moduleRequirementModal");
  if (modal) return modal;
  modal = document.createElement("div");
  modal.id = "moduleRequirementModal";
  modal.className = "modal hidden";
  document.body.appendChild(modal);
  return modal;
}
function showRequirementDecision(payload, data) {
  return new Promise((resolve) => {
    const modal = ensureRequirementModal();
    const missingRows = (data.missing_requires || []).map((item) => `<li>${escapeHtml(formatRequirePath(item))}</li>`).join("");
    modal.innerHTML = `<div class="modal-card"><div class="modal-header"><h2>运行前依赖检查</h2><button id="moduleRequirementCancelBtn" class="btn ghost">关闭</button></div><div class="preview-content"><p>${escapeHtml(requirementSummary(payload, data))}</p><div class="muted">缺失文件</div><ul>${missingRows || "<li>未识别到缺失项</li>"}</ul></div><div class="action-row"><button id="moduleRequirementForceBtn" class="btn danger">仍然强制只跑当前模块</button><button id="moduleRequirementRecommendedBtn" class="btn primary">从推荐模块开始运行</button></div></div>`;
    modal.classList.remove("hidden");
    $("moduleRequirementCancelBtn").onclick = () => { modal.classList.add("hidden"); resolve("cancel"); };
    $("moduleRequirementForceBtn").onclick = () => { modal.classList.add("hidden"); resolve("force"); };
    $("moduleRequirementRecommendedBtn").onclick = () => { modal.classList.add("hidden"); resolve("recommended"); };
  });
}
async function checkSingleModuleRequirements(payload, endpoint) {
  if (endpoint !== "/api/jobs/start" || !payload.only_module || payload.force_only_module) return payload;
  const runDir = targetRunDirForPayload(payload);
  if (!runDir) {
    alert("只跑单个模块前需要先填写项目 ID，或打开一个已有项目。");
    return null;
  }
  const data = await api(`/api/module-requirements?run_dir=${encodeURIComponent(runDir)}&module=${encodeURIComponent(payload.only_module)}`);
  if (data.can_run) return payload;
  const decision = await showRequirementDecision(payload, data);
  if (decision === "force") return { ...payload, skip_dependency_check: true, force_only_module: true };
  if (decision === "recommended") return { ...payload, only_module: "", from_module: data.recommended_from_module || payload.only_module };
  return null;
}
async function launchJob(payload, endpoint = "/api/jobs/start") {
  const data = await api(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  state.currentJob = data.job; state.logLines = [];
  $("liveLog").textContent = "任务已启动，等待输出...";
  if ($("stopBtn")) $("stopBtn").disabled = false;
  connectEvents(state.currentJob.id); updateJobMini(); switchView("dashboard");
  return data.job;
}
async function startJob(extra, endpoint = "/api/jobs/start") {
  const payload = await checkSingleModuleRequirements(getPayload(extra), endpoint);
  if (!payload) return null;
  return launchJob(payload, endpoint);
}
async function stopCurrentJob() { if (state.currentJob) await api(`/api/jobs/${state.currentJob.id}/stop`, { method: "POST" }); }
async function openProject(projectId) {
  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/snapshot`);
  state.currentSnapshot = data.snapshot;
  state.currentJob = null;
  await renderSnapshot();
  switchView("dashboard");
}
async function continueProject(projectId) {
  const data = await api(`/api/projects/${encodeURIComponent(projectId)}/snapshot`);
  const repair = data.snapshot?.repair_index || {};
  const moduleName = repair.earliest_problem_module || "01_novel_parser";
  return startJob({ project_id: projectId, from_module: moduleName, only_module: "" });
}
async function rerunProjectFromStart(projectId) { return startJob({ project_id: projectId, from_module: "01_novel_parser", only_module: "" }); }
async function archiveProject(projectId) {
  await api(`/api/projects/${encodeURIComponent(projectId)}/archive`, { method: "POST" });
  await loadProjects();
}

function connectEvents(jobId) {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource(`/api/jobs/${jobId}/events`);
  state.eventSource.addEventListener("log", (ev) => { const event = JSON.parse(ev.data); state.logLines.push(event.payload.line); state.logLines = state.logLines.slice(-800); $("liveLog").textContent = state.logLines.join("\n"); $("liveLog").scrollTop = $("liveLog").scrollHeight; });
  state.eventSource.addEventListener("snapshot", async (ev) => { const event = JSON.parse(ev.data); state.currentSnapshot = event.payload; await renderSnapshot(); });
  state.eventSource.addEventListener("job_started", (ev) => { const event = JSON.parse(ev.data); state.logLines.push(`[任务] ${event.payload.kind || "pipeline"} · ${event.payload.run_dir}`); $("liveLog").textContent = state.logLines.join("\n"); updateJobMini(); });
  state.eventSource.addEventListener("job_finished", (ev) => { const event = JSON.parse(ev.data); state.currentJob.status = event.payload.status; state.currentJob.return_code = event.payload.return_code; if ($("stopBtn")) $("stopBtn").disabled = true; updateJobMini(); refreshAll(); });
  state.eventSource.addEventListener("job_error", (ev) => { const event = JSON.parse(ev.data); state.logLines.push(`[错误] ${event.payload.error}`); $("liveLog").textContent = state.logLines.join("\n"); });
}
function updateJobMini() {
  if (!state.currentJob) { $("currentJobMini").textContent = "暂无任务"; $("metricJob").textContent = "无"; return; }
  $("currentJobMini").innerHTML = `<strong>${state.currentJob.id}</strong><br>${badge(state.currentJob.status)}<br><span class="muted">${state.currentJob.kind || "pipeline"}</span><br><span class="muted">${state.currentJob.run_dir}</span>`;
  $("metricJob").textContent = state.currentJob.id;
}

async function renderSnapshot() {
  const snap = state.currentSnapshot; if (!snap) return;
  const issues = collectIssues(snap.modules || []);
  $("metricRunStatus").textContent = statusLabel(snap.summary_status);
  $("metricOutputs").textContent = (snap.important_outputs || []).length;
  $("metricIssues").textContent = issues.length + Number(snap.data_link_check?.summary?.failed || 0);
  const heroBadge = $("heroStatusBadge"); if (heroBadge) heroBadge.outerHTML = badge(snap.summary_status).replace("badge", "badge").replace(">", ` id="heroStatusBadge">`);
  renderProgress(snap.modules || []); renderTimeline(snap.modules || []); renderStages(snap.modules || []); renderOutputs(snap.important_outputs || []); renderAssetSummaries(snap); renderRetryCenter([...issues, ...collectDataLinkIssues(snap)]); renderStructuredEvents(snap.events || []);
  await renderAssetCardGrid(snap); await renderStoryboardWorkspace(snap);
}
function renderProgress(modules) { const total = modules.length || state.displayPipeline.length || 1; const done = modules.filter((m) => ["success", "skipped"].includes(m.status)).length; const bar = $("pipelineProgressBar"); if (bar) bar.style.width = `${Math.round((done / total) * 100)}%`; }
function renderTimeline(modules = null) {
  const data = modules || state.displayPipeline.map((name) => ({ name, status: "pending", message: name === "00_main_controller" ? "等待自检 / 数据链路检查" : "等待" }));
  $("pipelineTimeline").innerHTML = data.map((m, i) => `<div class="timeline-item status-${m.status || "pending"}"><div class="index">${String(i).padStart(2, "0")}</div><div class="name">${moduleName(m.name)}</div><div class="muted">${escapeHtml(m.name || "")}</div>${badge(m.status)}<p>${m.message || ""}</p>${m.duration_seconds ? `<div class="muted">耗时 ${m.duration_seconds}s</div>` : ""}</div>`).join("");
}
function renderStages(modules) {
  const groups = modules.filter((m) => (m.stages || []).length || m.name === "00_main_controller");
  if (!groups.length) { $("stageExplorer").innerHTML = `<div class="muted">暂无阶段输出。可以先运行 00–10 数据链路检查，或启动 01–10 后查看 ABCDE 阶段卡片。</div>`; return; }
  $("stageExplorer").innerHTML = groups.map((m) => {
    const stages = m.stages || [];
    if (m.name === "00_main_controller" && state.currentSnapshot?.data_link_check?.results) return renderDataLinkGroup(state.currentSnapshot.data_link_check);
    const current = m.current_stage?.current_stage_id ? ` · 当前 ${m.current_stage.current_stage_id} ${m.current_stage.current_stage_name || ""}（${statusLabel(m.current_stage.status)}）` : "";
    return `<div class="module-stage-group"><div class="module-stage-header"><div><strong>${moduleName(m.name)}</strong><div class="muted">${escapeHtml(m.name)} · 阶段 ${stages.length} 个${escapeHtml(current)}</div></div>${badge(m.status)}</div><div class="stage-grid detailed-stage-grid">${stages.map((s) => renderStageCard(s, m.current_stage)).join("")}</div></div>`;
  }).join("");
}
function renderDataLinkGroup(report) {
  const results = report.results || [];
  return `<div class="module-stage-group"><div class="module-stage-header"><div><strong>00–10 数据链路检查</strong><div class="muted">总数 ${report.summary?.total || 0} · 通过 ${report.summary?.passed || 0} · 失败 ${report.summary?.failed || 0}</div></div>${badge(report.summary?.passed_all ? "success" : "failed")}</div><div class="stage-grid detailed-stage-grid">${results.slice(0, 120).map((r) => `<div class="stage-card detailed-stage-card"><div class="stage-name">${escapeHtml(r.item)}</div><div class="muted">${escapeHtml(r.message)}</div>${badge(r.status)}${r.path ? `<div class="card-actions"><button class="btn small" onclick="previewFile('${escapeAttr(r.path)}')">查看文件</button></div>` : ""}</div>`).join("")}</div></div>`;
}
function renderStageCard(s, currentStage = {}) {
  const sid = s.stage_id || s.name || "stage"; const status = s.passed === true ? "success" : s.passed === false ? "needs_review" : "pending";
  const active = String(currentStage?.current_stage_id || "") === String(sid).slice(0, 3);
  return `<div class="stage-card detailed-stage-card ${active ? "active" : ""}"><div class="stage-name">${escapeHtml(stageName(sid))}</div><div class="muted">文件：${escapeHtml(s.name || "-")}</div><div class="stage-score-row"><div><div class="score">${s.score ?? "-"}</div><div class="muted">阶段评分</div></div><div>${badge(active ? currentStage.status : status)}</div></div><div class="card-meta-grid"><div class="card-meta"><span>问题数</span><strong>${s.issues_count ?? 0}</strong></div><div class="card-meta"><span>通过</span><strong>${s.passed === true ? "是" : s.passed === false ? "否" : "待定"}</strong></div></div><div class="card-actions"><button class="btn small" onclick="previewFile('${s.path}')">查看阶段输出</button></div></div>`;
}

function collectIssues(modules) {
  const issues = [];
  for (const m of modules) {
    if (["failed", "blocked"].includes(m.status)) issues.push({ title: `${moduleName(m.name)} ${statusLabel(m.status)}`, detail: m.message || "模块未通过", level: "problem" });
    for (const s of m.stages || []) if (s.passed === false || Number(s.issues_count || 0) > 0) issues.push({ title: `${moduleName(m.name)} / ${stageName(s.stage_id || s.name)}`, detail: `评分 ${s.score ?? "-"}，问题 ${s.issues_count ?? 0} 个`, level: "problem", path: s.path });
    const q = m.quality || {}; if (q.needs_review || q.needs_retry || q.schema_validation_passed === false || q.passed_all === false) issues.push({ title: `${moduleName(m.name)} 总检需复核`, detail: JSON.stringify(q).slice(0, 220), level: "problem" });
  }
  return issues;
}
function collectDataLinkIssues(snap) { return (snap.data_link_check?.results || []).filter((r) => r.status === "fail").map((r) => ({ title: `链路检查失败：${r.item}`, detail: r.message, level: "problem", path: r.path })); }
function renderRetryCenter(issues) { const wrap = $("retryCenter"); if (!wrap) return; if (!issues.length) { wrap.innerHTML = `<div class="retry-item ok"><div class="retry-title">暂无集中返工问题</div><div class="muted">运行后如果出现低分、schema 校验失败、上游阻塞，这里会集中显示。</div></div>`; return; } wrap.innerHTML = issues.map((item) => `<div class="retry-item ${item.level}"><div class="retry-title">${escapeHtml(item.title)}</div><div class="muted">${escapeHtml(item.detail || "")}</div>${item.path ? `<button class="btn small" onclick="previewFile('${escapeAttr(item.path)}')">查看问题文件</button>` : ""}</div>`).join(""); }
function classifyEvent(event) {
  const type = String(event.event_type || "");
  if (type.includes("failed") || type.includes("error") || type.includes("validation")) return "错误事件";
  if (type.includes("stage")) return "阶段事件";
  if (type.includes("artifact") || type.includes("written")) return "产物事件";
  return "普通日志";
}
function ensureStructuredEventsPanel() {
  let panel = $("structuredEventsPanel");
  if (panel) return panel;
  const liveLog = $("liveLog");
  if (!liveLog?.parentElement) return null;
  panel = document.createElement("div");
  panel.id = "structuredEventsPanel";
  panel.className = "retry-list";
  liveLog.parentElement.appendChild(panel);
  return panel;
}
function renderStructuredEvents(events) {
  const panel = ensureStructuredEventsPanel();
  if (!panel) return;
  const groups = { "普通日志": [], "阶段事件": [], "错误事件": [], "产物事件": [] };
  for (const event of events.slice(-80)) (groups[classifyEvent(event)] || groups["普通日志"]).push(event);
  panel.innerHTML = Object.entries(groups).map(([title, rows]) => {
    const body = rows.slice(-8).map((event) => `<div class="muted">${escapeHtml(event.time || "")} · ${escapeHtml(event.module || "")} ${event.stage_id ? `· ${escapeHtml(event.stage_id)}` : ""} · ${escapeHtml(event.event_type || "")} · ${escapeHtml(event.message || "")}</div>`).join("");
    return `<div class="retry-item"><div class="retry-title">${title}（${rows.length}）</div>${body || '<div class="muted">暂无</div>'}</div>`;
  }).join("");
}
function renderOutputs(outputs) { if (!outputs.length) { $("outputList").innerHTML = `<div class="muted">暂无最终产物。</div>`; return; } $("outputList").innerHTML = outputs.map((o) => `<div class="output-item"><div><div class="output-name">${escapeHtml(o.name)}</div><div class="output-path">${escapeHtml(o.path)}</div></div><button class="btn small" onclick="previewFile('${o.path}')">预览</button></div>`).join(""); }
function renderAssetSummaries(snap) { const outputs = snap.important_outputs || []; const has = (suffix) => outputs.some((o) => o.path.endsWith(suffix)); $("characterSummary").textContent = has("03_character_system/characters.json") ? "角色资产已生成，可在下方编辑每个角色提示词。" : "等待 03 输出"; $("sceneSummary").textContent = has("04_scene_system/scenes.json") ? "场景资产已生成，可在下方编辑每个场景提示词。" : "等待 04 输出"; $("propSummary").textContent = has("05_prop_system/props.json") ? "道具资产已生成，可在下方编辑每个道具提示词。" : "等待 05 输出"; }
async function loadJsonFromRun(relPath) { const rel = currentRunDir(); if (!rel) return null; try { const data = await api(`/api/file?path=${encodeURIComponent(`${rel}/${relPath}`)}`); return data.type === "json" ? data.content : null; } catch (_) { return null; } }
async function renderAssetCardGrid(snap) { const wrap = $("assetCardGrid"); if (!wrap) return; if (!snap) { wrap.innerHTML = `<div class="muted">运行 03/04/05 后，这里会显示可编辑资产卡。</div>`; return; } const [characters, scenes, props] = await Promise.all([loadJsonFromRun("03_character_system/characters.json"), loadJsonFromRun("04_scene_system/scenes.json"), loadJsonFromRun("05_prop_system/props.json")]); const cards = []; for (const item of characters?.characters || []) cards.push(assetCard("character", item.canonical_name, item.asset_level, item.default_costume_id, item.appearance || item.costume || "", buildCharacterPrompt(item))); for (const item of scenes?.scenes || []) cards.push(assetCard("scene", item.canonical_scene_name, item.asset_level, item.parent_scene || "", item.reference_image_plan || "", buildScenePrompt(item))); for (const item of props?.props || []) cards.push(assetCard("prop", item.canonical_prop_name, item.asset_level, item.wearable_policy || "", item.reference_image_plan || "", buildPropPrompt(item))); wrap.innerHTML = cards.length ? cards.join("") : `<div class="muted">暂无资产卡。请先运行 03/04/05。</div>`; restorePromptValues(); }
function assetCard(type, title, level, meta, desc, prompt) { const key = `asset:${type}:${title}`; return `<div class="editable-card"><div class="editable-card-header"><div><div class="editable-title">${escapeHtml(title || "未命名资产")}</div><div class="editable-subtitle">${typeLabel(type)} · ${escapeHtml(level || "未分级")}</div></div>${badge("pending")}</div><div class="card-meta-grid"><div class="card-meta"><span>引用信息</span><strong>${escapeHtml(meta || "-")}</strong></div><div class="card-meta"><span>生成状态</span><strong>等待 07 接入</strong></div></div><div class="image-slot">图片预览位</div><textarea class="prompt-editor" data-prompt-key="${escapeAttr(key)}">${escapeHtml(prompt || desc || "")}</textarea><div class="card-actions"><button class="btn small" onclick="savePromptDraft('${escapeAttr(key)}')">保存提示词</button><button class="btn small primary" onclick="regenerateImage('${escapeAttr(key)}')">重新生成图片</button></div></div>`; }
function typeLabel(type) { return { character: "角色资产", scene: "场景资产", prop: "道具资产", frame: "分镜帧" }[type] || type; }
function buildCharacterPrompt(item) { return [`角色：${item.canonical_name || ""}`, `外观：${toText(item.appearance)}`, `服装版本：${toText(item.costume_variants || item.costume)}`, `定妆照需求：${toText(item.reference_image_plan)}`, "风格：电视剧电影真人写实，中国古代语境，真实光照，清晰细节，避免现代物品。"].join("\n"); }
function buildScenePrompt(item) { return [`场景：${item.canonical_scene_name || ""}`, `层级：${item.asset_level || ""}`, `参考图计划：${toText(item.reference_image_plan)}`, "风格：古代中国影视剧真实场景，空间结构清晰，光影自然，无现代元素。"].join("\n"); }
function buildPropPrompt(item) { return [`道具：${item.canonical_prop_name || ""}`, `道具级别：${item.asset_level || ""}`, `穿戴策略：${item.wearable_policy || ""}`, `参考图计划：${toText(item.reference_image_plan)}`, "风格：真实材质，古代器物，中国古风影视质感，无现代工业痕迹。"].join("\n"); }
async function renderStoryboardWorkspace(snap) { const wrap = $("storyboardWorkspace"); if (!wrap) return; if (!snap) { wrap.innerHTML = `<div class="muted">暂无分镜数据。运行 06 单帧分镜后这里会显示分镜卡片。</div>`; return; } const storyboard = await loadJsonFromRun("06_storyboard/storyboard.json"); const frames = storyboard?.frames || []; if (!frames.length) { wrap.innerHTML = `<div class="muted">等待 06_storyboard/storyboard.json 输出。</div>`; return; } wrap.classList.add("editable-card-grid"); wrap.innerHTML = frames.slice(0, 80).map((frame) => frameCard(frame)).join(""); restorePromptValues(); }
function frameCard(frame) { const id = frame.frame_id || `frame_${frame.sequence_index || ""}`; const key = `frame:${id}`; const characters = (frame.characters || []).map((c) => `${c.canonical_name || ""}/${c.costume_id || ""}`).filter(Boolean).join("，"); const scene = frame.scene?.canonical_scene_name || frame.canonical_scene_name || ""; const prompt = [`分镜：${id}`, `场景：${scene}`, `角色：${characters}`, `动作：${frame.story_action || frame.action || ""}`, `构图：${frame.composition_notes || ""}`, `连续性：${frame.continuity_notes || ""}`, "风格：电视剧电影真人写实，中国古代语境，角色服装与资产库一致，画面稳定，避免现代物品。"].join("\n"); return `<div class="editable-card storyboard-card"><div class="editable-card-header"><div><div class="editable-title">${escapeHtml(id)}</div><div class="editable-subtitle">第 ${frame.sequence_index ?? "-"} 帧 · ${escapeHtml(scene || "未绑定场景")}</div></div>${badge("pending")}</div><div class="card-meta-grid"><div class="card-meta"><span>角色</span><strong>${escapeHtml(characters || "-")}</strong></div><div class="card-meta"><span>图像状态</span><strong>等待 07 接入</strong></div></div><div class="image-slot">分镜图预览位</div><textarea class="prompt-editor" data-prompt-key="${escapeAttr(key)}">${escapeHtml(prompt)}</textarea><div class="card-actions"><button class="btn small" onclick="savePromptDraft('${escapeAttr(key)}')">保存提示词</button><button class="btn small primary" onclick="regenerateImage('${escapeAttr(key)}')">重新生成本帧</button></div></div>`; }

function savePromptDraft(key) { const el = document.querySelector(`[data-prompt-key="${cssEscape(key)}"]`); if (!el) return; localStorage.setItem(`ai_drama_prompt:${key}`, el.value); toast(`已保存：${key}`); }
function restorePromptValues() { document.querySelectorAll("[data-prompt-key]").forEach((el) => { const key = el.dataset.promptKey; const saved = localStorage.getItem(`ai_drama_prompt:${key}`); if (saved !== null) el.value = saved; }); }
function regenerateImage(key) { savePromptDraft(key); toast("已保存提示词。07 图片生成模块接入后，这里会触发单项重绘。") }
function toast(message) { console.log(message); alert(message); }
function currentRunDir() { return state.currentSnapshot?.run_dir || state.currentJob?.run_dir || ""; }
async function previewFile(path) { try { const data = await api(`/api/file?path=${encodeURIComponent(path)}`); $("previewTitle").textContent = data.path || path; if (data.type === "json") $("previewContent").textContent = JSON.stringify(data.content, null, 2); else if (data.type === "image") $("previewContent").innerHTML = `<img src="${data.url}" style="max-width:100%;border-radius:16px" />`; else if (data.type === "media") $("previewContent").textContent = `媒体文件：${data.path}\n大小：${data.size || 0} bytes\nURL：${data.url}`; else $("previewContent").textContent = data.content || `二进制文件，大小 ${data.size || 0} bytes`; $("previewModal").classList.remove("hidden"); } catch (err) { $("previewTitle").textContent = "预览失败"; $("previewContent").textContent = String(err); $("previewModal").classList.remove("hidden"); } }
function toText(value) { if (value === null || value === undefined) return ""; return typeof value === "string" ? value : JSON.stringify(value, null, 2); }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch])); }
function escapeAttr(value) { return escapeHtml(value).replace(/'/g, "&#39;"); }
function cssEscape(value) { return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"'); }

window.previewFile = previewFile;
window.savePromptDraft = savePromptDraft;
window.regenerateImage = regenerateImage;
window.getPayload = getPayload;
window.startJob = startJob;
window.connectEvents = connectEvents;
window.openProject = openProject;
window.continueProject = continueProject;
window.rerunProjectFromStart = rerunProjectFromStart;
window.archiveProject = archiveProject;
init().catch((err) => { console.error(err); if ($("liveLog")) $("liveLog").textContent = String(err); });
