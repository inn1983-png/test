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
  "09A": "输入检查", "09PRE": "前置自检", "09B": "视频规划", "09C": "LTX执行", "09D": "视频总检",
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

const ISSUE_TYPE_NAMES = {
  "missing_dependency": "缺少依赖",
  "schema_failed": "Schema 校验失败",
  "stage_quality_failed": "阶段质量未通过",
  "llm_json_parse_failed": "LLM JSON 解析失败",
  "llm_output_truncated": "LLM 输出截断",
  "upstream_blocking": "上游阻塞",
  "image_failed_frames": "图片帧失败",
  "audio_failed_segments": "音频段失败",
  "video_failed_segments": "视频段失败",
  "final_export_not_ready": "最终视频未生成",
};

const ACTION_NAMES = {
  "rerun_from_upstream": "从上游模块重跑",
  "rerun_module": "重跑当前模块",
  "retry_failed_frames": "重跑失败帧",
  "retry_failed_segments": "重跑失败段",
  "check_ffmpeg_and_upstream": "检查 ffmpeg 和上游",
};

async function renderRepairCenter() {
  const wrap = $("repairCenter");
  if (!wrap) return;
  if (!state.currentSnapshot) {
    wrap.innerHTML = `<div style="color:var(--muted);padding:20px">选择项目后查看返工中心</div>`;
    return;
  }
  const repair = state.currentSnapshot.repair_index;
  if (!repair || !repair.issues || !repair.issues.length) {
    wrap.innerHTML = `<div class="repair-empty"><div class="repair-empty-icon">✓</div><div>所有模块状态正常，无需返工</div></div>`;
    return;
  }
  const summary = repair.summary || {};
  const issues = repair.issues || [];
  let html = `<div class="repair-summary">
    <div class="repair-stat"><span class="repair-stat-num">${summary.total_issues || 0}</span><span class="repair-stat-label">总问题</span></div>
    <div class="repair-stat stat-blocking"><span class="repair-stat-num">${summary.blocking_issues || 0}</span><span class="repair-stat-label">阻塞</span></div>
    <div class="repair-stat stat-retryable"><span class="repair-stat-num">${summary.retryable_issues || 0}</span><span class="repair-stat-label">可重试</span></div>
  </div>`;
  if (summary.recommended_from_module) {
    html += `<div class="repair-rec">建议从 <strong>${mName(summary.recommended_from_module)}</strong> 开始重跑</div>`;
  }
  html += `<div class="repair-issues">`;
  for (const issue of issues) {
    const canRun = issue.can_run_current_module;
    const issueType = issue.issue_type || "unknown";
    const issueLabel = ISSUE_TYPE_NAMES[issueType] || issueType;
    const actionLabel = ACTION_NAMES[issue.suggested_action] || issue.suggested_action || "";
    const moduleLabel = mName(issue.module || "");
    const stageLabel = issue.stage_id || "";
    const isBlocking = !canRun;
    const cls = isBlocking ? "repair-issue blocking" : "repair-issue retryable";
    html += `<div class="${cls}">
      <div class="ri-header">
        <span class="ri-module">${esc(moduleLabel)}</span>
        ${stageLabel ? `<span class="ri-stage">${esc(stageLabel)}</span>` : ""}
        <span class="ri-type">${esc(issueLabel)}</span>
        ${isBlocking ? `<span class="ri-badge blocking">阻塞</span>` : ""}
      </div>
      <div class="ri-message">${esc(issue.issue_message || "")}</div>
      <div class="ri-actions">`;
    if (canRun && issue.recommended_only_module) {
      const retryScope = getRetryScope(issue);
      html += `<button class="btn small primary" onclick="repairRunModule('${escAttr(issue.recommended_only_module)}', ${retryScope})">${actionLabel || "重跑当前模块"}</button>`;
    }
    if (issue.recommended_from_module) {
      html += `<button class="btn small" onclick="repairRunFrom('${escAttr(issue.recommended_from_module)}')">从 ${mName(issue.recommended_from_module)} 开始跑</button>`;
    }
    if (!canRun) {
      html += `<span class="ri-hint">当前模块缺少依赖，请先跑上游</span>`;
    }
    html += `</div></div>`;
  }
  html += `</div>`;
  wrap.innerHTML = html;
}

function getRetryScope(issue) {
  if (issue.issue_type === "image_failed_frames") return `{image_retry_scope:"failed_frames"}`;
  if (issue.issue_type === "audio_failed_segments") return `{audio_retry_scope:"failed_segments"}`;
  if (issue.issue_type === "video_failed_segments") return `{video_retry_scope:"failed_segments"}`;
  return "{}";
}

async function repairRunModule(moduleName, retryScope) {
  const extra = { only_module: moduleName };
  if (retryScope && retryScope.image_retry_scope) extra.image_retry_scope = retryScope.image_retry_scope;
  if (retryScope && retryScope.audio_retry_scope) extra.audio_retry_scope = retryScope.audio_retry_scope;
  if (retryScope && retryScope.video_retry_scope) extra.video_retry_scope = retryScope.video_retry_scope;
  await startJob(extra);
}

async function repairRunFrom(moduleName) {
  await startJob({ from_module: moduleName });
}

window.repairRunModule = repairRunModule;
window.repairRunFrom = repairRunFrom;

async function runHealthCheck() {
  const wrap = $("repairCenter");
  if (!wrap) return;
  wrap.innerHTML = `<div style="padding:20px;color:var(--muted)">正在运行系统健康检查...</div>`;
  try {
    const result = await api("/api/system/health-check", { method: "POST" });
    const checks = result.checks || [];
    const summary = result.summary || {};
    let html = `<div class="repair-summary">
      <div class="repair-stat"><span class="repair-stat-num" style="color:var(--success)">${summary.passed || 0}</span><span class="repair-stat-label">通过</span></div>
      <div class="repair-stat stat-retryable"><span class="repair-stat-num">${summary.warning || 0}</span><span class="repair-stat-label">警告</span></div>
      <div class="repair-stat stat-blocking"><span class="repair-stat-num">${summary.failed || 0}</span><span class="repair-stat-label">失败</span></div>
    </div>`;
    const groups = {};
    for (const check of checks) {
      const g = check.group || "Other";
      if (!groups[g]) groups[g] = [];
      groups[g].push(check);
    }
    for (const [groupName, groupChecks] of Object.entries(groups)) {
      html += `<div style="margin-top:12px;font-weight:800;font-size:13px;color:var(--primary)">${esc(groupName)}</div>`;
      html += `<div class="repair-issues">`;
      for (const check of groupChecks) {
        const statusIcon = check.status === "passed" ? "✓" : check.status === "warning" ? "⚠" : "✗";
        const statusColor = check.status === "passed" ? "var(--success)" : check.status === "warning" ? "var(--warning)" : "var(--danger)";
        html += `<div class="repair-issue ${check.status === "failed" ? "blocking" : check.status === "warning" ? "retryable" : ""}">
          <div class="ri-header">
            <span style="color:${statusColor};font-weight:800">${statusIcon}</span>
            <span class="ri-type">${esc(check.check_id || "")}</span>
          </div>
          <div class="ri-message">${esc(check.message || "")}</div>
          ${check.fix_hint ? `<div class="ri-hint" style="color:var(--muted)">修复建议：${esc(check.fix_hint)}</div>` : ""}
        </div>`;
      }
      html += `</div>`;
    }
    wrap.innerHTML = html;
  } catch (err) {
    wrap.innerHTML = `<div style="padding:20px;color:var(--danger)">健康检查失败: ${esc(String(err))}</div>`;
  }
}

window.runHealthCheck = runHealthCheck;

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
    renderRepairCenter();
    renderStepRunGrid();
  } else {
    renderPipeline();
    renderStepRunGrid();
    renderRepairCenter();
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
    renderRepairCenter();
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
  renderRepairCenter();
  updateTopbar();
}

async function previewFile(path) {
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    $("previewTitle").textContent = data.path || path;
    const isPlaceholder = data.path && data.path.includes(".placeholder.txt");
    if (data.type === "json") {
      $("previewContent").textContent = JSON.stringify(data.content, null, 2);
    } else if (data.type === "image") {
      $("previewContent").innerHTML = `<img src="${data.url}" style="max-width:100%;border-radius:12px" />`;
    } else if (data.type === "media") {
      if (data.path && data.path.endsWith(".mp4")) {
        const snapshot = state.currentSnapshot;
        const videoReady = snapshot && snapshot.final_video_ready === true;
        if (videoReady) {
          $("previewContent").innerHTML = `<div style="padding:16px;background:var(--surface);border-radius:8px;margin-bottom:12px"><strong style="color:var(--success)">✓ 最终视频已生成</strong><br/><span style="color:var(--muted);font-size:12px">大小：${data.size || 0} bytes</span></div><video src="${data.url}" controls style="max-width:100%;border-radius:12px"></video>`;
        } else {
          const placeholderPath = snapshot && snapshot.final_video_placeholder_path;
          let placeholderContent = "";
          if (placeholderPath) {
            try {
              const placeholderData = await api(`/api/file?path=${encodeURIComponent(placeholderPath)}`);
              placeholderContent = esc(placeholderData.content || "");
            } catch (e) {}
          }
          $("previewContent").innerHTML = `<div style="padding:16px;background:var(--surface);border-radius:8px;margin-bottom:12px"><strong style="color:var(--warning)">⚠ 最终视频未生成，仅生成占位说明</strong><br/><span style="color:var(--muted);font-size:12px">final_video_ready=false，请检查 ffmpeg 是否可用或上游产物是否完整</span></div>${placeholderContent ? `<pre style="white-space:pre-wrap;font-size:12px">${placeholderContent}</pre>` : ""}`;
        }
      } else {
        $("previewContent").textContent = `媒体文件：${data.path}\n大小：${data.size || 0} bytes`;
      }
    } else if (isPlaceholder) {
      $("previewContent").innerHTML = `<div style="padding:16px;background:var(--surface);border-radius:8px;margin-bottom:12px"><strong style="color:var(--warning)">⚠ 最终视频未生成，仅生成占位说明</strong><br/><span style="color:var(--muted);font-size:12px">dry_run 或 ffmpeg 不可用时不会创建 final.mp4，只创建占位说明文件</span></div><pre style="white-space:pre-wrap;font-size:12px">${esc(data.content || "")}</pre>`;
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
    return `<button class="step-btn ${cls}" onclick="runSingleModule('${escAttr(name)}')" onmouseenter="checkModuleDeps('${escAttr(name)}')"><span class="step-id">${name.slice(0, 2)}</span><span class="step-name">${mName(name)}</span><span class="step-status">${statusText(s)}</span></button>`;
  }).join("");
}

async function runSingleModule(moduleName) {
  const skipDeps = $("skipDepCheck") && $("skipDepCheck").checked;
  const extra = { only_module: moduleName };
  if (skipDeps) extra.skip_dependency_check = "1";
  await startJob(extra);
}

async function checkModuleDeps(moduleName) {
  const hint = $("depHint");
  if (!hint) return;
  if (!moduleName) { hint.innerHTML = ""; return; }
  if (moduleName === "01_novel_parser") {
    hint.innerHTML = `<span style="color:var(--success)">✓ 01 无前置依赖，可单独运行</span>`;
    return;
  }
  hint.innerHTML = `<span style="color:var(--muted)">检查依赖中...</span>`;
  try {
    const snapshot = state.currentSnapshot;
    const runDir = snapshot ? snapshot.run_dir : "";
    const params = new URLSearchParams({ module: moduleName });
    if (runDir) params.set("run_dir", runDir);
    const result = await api(`/api/module-requirements?${params}`);
    if (result.can_run) {
      hint.innerHTML = `<span style="color:var(--success)">✓ 依赖已满足，可单独运行</span>`;
    } else {
      const missing = (result.missing_requires || []).map(m => `${m.module}.${m.name || "?"}`).join("、");
      const rec = result.recommended_from_module || moduleName;
      hint.innerHTML = `<span style="color:var(--danger)">✗ 缺少依赖：${esc(missing)}</span><br/><span style="color:var(--muted)">建议从 ${mName(rec)} 开始跑，或勾选"跳过依赖检查"</span>`;
    }
  } catch (e) {
    hint.innerHTML = `<span style="color:var(--warning)">依赖检查失败: ${esc(String(e))}</span>`;
  }
}

init().catch((err) => { console.error(err); if ($("liveLog")) $("liveLog").textContent = String(err); });
