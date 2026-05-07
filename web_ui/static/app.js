const state = {
  pipeline: [],
  currentJob: null,
  currentSnapshot: null,
  eventSource: null,
  logLines: [],
};

const $ = (id) => document.getElementById(id);

function statusLabel(status) {
  const map = {
    success: "完成",
    running: "运行中",
    failed: "失败",
    blocked: "阻塞",
    skipped: "跳过",
    pending: "等待",
    queued: "排队",
    not_started: "未开始",
    needs_review: "需复核",
    stopping: "停止中",
  };
  return map[status] || status || "未知";
}

function badge(status) {
  const cls = String(status || "pending").replace(/[^a-zA-Z0-9_-]/g, "");
  return `<span class="badge ${cls}">${statusLabel(status)}</span>`;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function init() {
  bindNav();
  bindActions();
  await loadPipeline();
  await refreshAll();
}

function bindNav() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      btn.classList.add("active");
      $(`view-${btn.dataset.view}`).classList.add("active");
    });
  });
}

function bindActions() {
  $("refreshBtn").addEventListener("click", refreshAll);
  $("startBtn").addEventListener("click", () => startJob({}));
  $("startTextPhaseBtn").addEventListener("click", () => startJob({ from_module: "01_novel_parser" }));
  $("stopBtn").addEventListener("click", stopCurrentJob);
  $("closePreviewBtn").addEventListener("click", () => $("previewModal").classList.add("hidden"));
  document.querySelectorAll(".preview-main-output").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = btn.closest(".asset-panel");
      const rel = currentRunDir();
      if (!rel) return;
      previewFile(`${rel}/${panel.dataset.output}`);
    });
  });
}

async function loadPipeline() {
  const data = await api("/api/pipeline");
  state.pipeline = Array.isArray(data.pipeline) ? data.pipeline : [];
  $("metricModules").textContent = state.pipeline.length;
  fillModuleSelects();
  renderTimeline();
}

function fillModuleSelects() {
  const from = $("fromModuleInput");
  const only = $("onlyModuleInput");
  from.innerHTML = `<option value="">从头开始</option>` + state.pipeline.map((m) => `<option value="${m}">${m}</option>`).join("");
  only.innerHTML = `<option value="">不限制</option>` + state.pipeline.map((m) => `<option value="${m}">${m}</option>`).join("");
}

async function refreshAll() {
  await loadProjects();
  if (state.currentJob) {
    const data = await api(`/api/jobs/${state.currentJob.id}/snapshot`);
    state.currentSnapshot = data.snapshot;
    renderSnapshot();
  } else {
    renderTimeline();
  }
}

async function loadProjects() {
  const data = await api("/api/projects");
  const projects = data.projects || [];
  const wrap = $("projectList");
  if (!projects.length) {
    wrap.innerHTML = `<div class="muted">暂无项目。可以先在生产控制台启动一次。</div>`;
    return;
  }
  wrap.innerHTML = projects.slice(0, 12).map((p) => `
    <div class="list-item">
      <div>
        <strong>${p.project_id}</strong>
        <div class="muted">${p.run_dir}</div>
      </div>
      <div>${badge(p.status)}</div>
    </div>
  `).join("");
}

function getPayload(extra) {
  const payload = {
    mode: $("modeInput").value,
    project_id: $("projectIdInput").value,
    book_id: $("bookIdInput").value,
    chapter_id: $("chapterIdInput").value,
    from_module: $("fromModuleInput").value,
    only_module: $("onlyModuleInput").value,
    novel_text: $("novelTextInput").value,
    llm_base_url: $("llmBaseUrlInput").value,
    llm_model: $("llmModelInput").value,
    llm_temperature: $("llmTemperatureInput").value,
    llm_timeout_sec: $("llmTimeoutInput").value,
    strict_order: $("strictOrderInput").checked,
    skip_validation: $("skipValidationInput").checked,
    skip_dependency_check: $("skipDependencyInput").checked,
    ...extra,
  };
  if (payload.only_module) payload.from_module = "";
  return payload;
}

async function startJob(extra) {
  const payload = getPayload(extra);
  const data = await api("/api/jobs/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.currentJob = data.job;
  state.logLines = [];
  $("liveLog").textContent = "任务已启动，等待输出...";
  $("stopBtn").disabled = false;
  connectEvents(state.currentJob.id);
  updateJobMini();
}

async function stopCurrentJob() {
  if (!state.currentJob) return;
  await api(`/api/jobs/${state.currentJob.id}/stop`, { method: "POST" });
}

function connectEvents(jobId) {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = new EventSource(`/api/jobs/${jobId}/events`);
  state.eventSource.addEventListener("log", (ev) => {
    const event = JSON.parse(ev.data);
    state.logLines.push(event.payload.line);
    if (state.logLines.length > 800) state.logLines = state.logLines.slice(-800);
    $("liveLog").textContent = state.logLines.join("\n");
    $("liveLog").scrollTop = $("liveLog").scrollHeight;
  });
  state.eventSource.addEventListener("snapshot", (ev) => {
    const event = JSON.parse(ev.data);
    state.currentSnapshot = event.payload;
    renderSnapshot();
  });
  state.eventSource.addEventListener("job_started", (ev) => {
    const event = JSON.parse(ev.data);
    state.logLines.push(`[JOB] ${event.payload.run_dir}`);
    updateJobMini();
  });
  state.eventSource.addEventListener("job_finished", (ev) => {
    const event = JSON.parse(ev.data);
    state.currentJob.status = event.payload.status;
    state.currentJob.return_code = event.payload.return_code;
    $("stopBtn").disabled = true;
    updateJobMini();
  });
  state.eventSource.addEventListener("job_error", (ev) => {
    const event = JSON.parse(ev.data);
    state.logLines.push(`[ERROR] ${event.payload.error}`);
    $("liveLog").textContent = state.logLines.join("\n");
  });
}

function updateJobMini() {
  if (!state.currentJob) {
    $("currentJobMini").textContent = "暂无任务";
    $("metricJob").textContent = "无";
    $("metricJobSub").textContent = "未运行";
    return;
  }
  $("currentJobMini").innerHTML = `<strong>${state.currentJob.id}</strong><br>${badge(state.currentJob.status)}<br><span class="muted">${state.currentJob.run_dir}</span>`;
  $("metricJob").textContent = state.currentJob.id;
  $("metricJobSub").textContent = statusLabel(state.currentJob.status);
}

function renderSnapshot() {
  const snap = state.currentSnapshot;
  if (!snap) return;
  $("metricRunStatus").textContent = statusLabel(snap.summary_status);
  $("metricOutputs").textContent = (snap.important_outputs || []).length;
  renderTimeline(snap.modules || []);
  renderStages(snap.modules || []);
  renderOutputs(snap.important_outputs || []);
  renderAssetSummaries(snap);
}

function renderTimeline(modules = null) {
  const data = modules || state.pipeline.map((name) => ({ name, status: "pending", message: "等待" }));
  $("pipelineTimeline").innerHTML = data.map((m, i) => `
    <div class="timeline-item">
      <div class="index">${String(i + 1).padStart(2, "0")}</div>
      <div class="name">${m.name}</div>
      ${badge(m.status)}
      <p>${m.message || ""}</p>
      ${m.duration_seconds ? `<div class="muted">耗时 ${m.duration_seconds}s</div>` : ""}
    </div>
  `).join("");
}

function renderStages(modules) {
  const groups = modules.filter((m) => (m.stages || []).length);
  if (!groups.length) {
    $("stageExplorer").innerHTML = `<div class="muted">暂无阶段输出。运行 01–06 后这里会出现 A/B/C/D/E 阶段卡片。</div>`;
    return;
  }
  $("stageExplorer").innerHTML = groups.map((m) => `
    <div class="module-stage-group">
      <div class="module-stage-header">
        <strong>${m.name}</strong>
        ${badge(m.status)}
      </div>
      <div class="stage-grid">
        ${m.stages.map((s) => `
          <div class="stage-card">
            <div class="stage-name">${s.stage_id || s.name}</div>
            <div>${s.passed === true ? badge("success") : s.passed === false ? badge("needs_review") : badge("pending")}</div>
            <div class="score">${s.score ?? "-"}</div>
            <div class="muted">问题 ${s.issues_count ?? 0} 个</div>
            <button class="btn small" onclick="previewFile('${s.path}')">查看输出</button>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

function renderOutputs(outputs) {
  if (!outputs.length) {
    $("outputList").innerHTML = `<div class="muted">暂无最终产物。</div>`;
    return;
  }
  $("outputList").innerHTML = outputs.map((o) => `
    <div class="output-item">
      <div>
        <div class="output-name">${o.name}</div>
        <div class="output-path">${o.path}</div>
      </div>
      <button class="btn small" onclick="previewFile('${o.path}')">预览</button>
    </div>
  `).join("");
}

function renderAssetSummaries(snap) {
  const outputs = snap.important_outputs || [];
  const has = (suffix) => outputs.some((o) => o.path.endsWith(suffix));
  $("characterSummary").textContent = has("03_character_system/characters.json") ? "角色资产已生成，可预览角色卡 JSON。" : "等待 03 输出";
  $("sceneSummary").textContent = has("04_scene_system/scenes.json") ? "场景资产已生成，可预览场景卡 JSON。" : "等待 04 输出";
  $("propSummary").textContent = has("05_prop_system/props.json") ? "道具资产已生成，可预览道具卡 JSON。" : "等待 05 输出";
}

function currentRunDir() {
  if (state.currentSnapshot?.run_dir) return state.currentSnapshot.run_dir;
  if (state.currentJob?.run_dir) return state.currentJob.run_dir;
  return "";
}

async function previewFile(path) {
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    $("previewTitle").textContent = data.path || path;
    if (data.type === "json") {
      $("previewContent").textContent = JSON.stringify(data.content, null, 2);
    } else {
      $("previewContent").textContent = data.content || `二进制文件，大小 ${data.size || 0} bytes`;
    }
    $("previewModal").classList.remove("hidden");
  } catch (err) {
    $("previewTitle").textContent = "预览失败";
    $("previewContent").textContent = String(err);
    $("previewModal").classList.remove("hidden");
  }
}

window.previewFile = previewFile;
init().catch((err) => {
  console.error(err);
  $("liveLog").textContent = String(err);
});
