const state = {
  pipeline: [],
  currentJob: null,
  currentSnapshot: null,
  eventSource: null,
  logLines: [],
  selectedModule: null,
  latestReviewedResult: null,
};

const MODULE_NAMES = {
  "00_style_system": "风格圣经",
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
  "10_final_assembly": "成片",
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

const STYLE_PRESETS = [
  ["ancient_live_action_realistic", "古装真人写实短剧"],
  ["ancient_gritty_realism", "古代粗粝现实主义"],
  ["ancient_palace_drama", "古装宫廷权谋剧"],
  ["ancient_war_epic", "古代战争史诗"],
  ["song_dynasty_slice_of_life", "宋韵市井生活剧"],
  ["tang_dynasty_romance", "盛唐华丽爱情剧"],
  ["ming_qing_mystery", "明清探案悬疑剧"],
  ["wuxia_live_action", "武侠真人电影感"],
  ["xianxia_cinematic", "仙侠电影感"],
  ["dark_fantasy_chinese", "东方暗黑奇幻"],
  ["modern_urban_drama", "现代都市真人短剧"],
  ["modern_suspense_thriller", "现代悬疑冷峻短剧"],
  ["modern_romance_idol", "现代偶像甜宠短剧"],
  ["republic_era_cinematic", "民国电影感"],
  ["cyberpunk_noir", "赛博朋克冷色 noir"],
  ["chinese_3d_animation", "中国风3D动画"],
  ["claymation_chinese_folk", "中国民俗黏土动画"],
  ["ink_wash_motion", "水墨国风动态绘本"],
];

const STYLE_STORAGE_KEY = "ai_drama_selected_style_preset";
const DEFAULT_STYLE = "ancient_live_action_realistic";

const MODULE_RESULT_FILES = {
  "00_style_system": "style_bible.json",
  "01_novel_parser": "novel_analysis.json",
  "02_script_writer": "script.json",
  "03_character_system": "characters.json",
  "04_scene_system": "scenes.json",
  "05_prop_system": "props.json",
  "06_storyboard": "storyboard.json",
  "07_storyboard_image": "image_manifest.json",
  "08_audio": "audio_timeline.json",
  "09_video": "video_manifest.json",
  "10_final_assembly": "final_manifest.json",
};

const MODULE_RESULT_TITLES = {
  "00_style_system": "风格圣经",
  "01_novel_parser": "小说理解结果",
  "02_script_writer": "剧本改编结果",
  "03_character_system": "角色提取结果",
  "04_scene_system": "场景提取结果",
  "05_prop_system": "道具提取结果",
  "06_storyboard": "分镜结果",
  "07_storyboard_image": "图片生成结果",
  "08_audio": "音频结果",
  "09_video": "视频结果",
  "10_final_assembly": "成片结果",
};

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

function getSelectedStylePreset() {
  const el = $("stylePresetInput");
  return String(el?.value || localStorage.getItem(STYLE_STORAGE_KEY) || DEFAULT_STYLE).trim() || DEFAULT_STYLE;
}

function getPayload(extra) {
  return {
    mode: "project",
    project_id: $("projectIdInput")?.value,
    novel_text: $("novelTextInput")?.value,
    style_preset: getSelectedStylePreset(),
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
  switchTab("stage");
  renderStageDetail();
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
  let html = "";

  if (MODULE_RESULT_FILES[state.selectedModule]) {
    html += `<div id="moduleResultSummary" class="module-result-summary"></div>`;
  }

  if (!stages.length) {
    html += `<div class="stage-detail-card"><h3>${esc(mName(m.name))}</h3><div style="color:var(--muted)">暂无阶段输出</div></div>`;
  } else {
    html += stages.map((s) => {
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

  html += `<div id="moduleReviewBox"></div>`;
  wrap.innerHTML = html;

  if (MODULE_RESULT_FILES[state.selectedModule]) {
    renderResultSummary(state.selectedModule);
  }
  renderReviewBox(state.selectedModule);
}

async function renderResultSummary(moduleName) {
  const wrap = $("moduleResultSummary");
  if (!wrap) return;
  wrap.innerHTML = `<div class="result-loading">正在读取模块成果...</div>`;
  const runDir = state.currentSnapshot?.run_dir;
  const file = MODULE_RESULT_FILES[moduleName];
  if (!runDir || !file) { wrap.innerHTML = ""; return; }
  const path = `${runDir}/${moduleName}/${file}`;
  let content = null;
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    if (data.type === "json") content = data.content;
  } catch (_) {}
  const rawButton = path ? `<button class="btn small ghost" onclick="previewFile('${escAttr(path)}')">查看原始 JSON</button>` : "";
  wrap.innerHTML = `<div class="result-header"><h3>${esc(MODULE_RESULT_TITLES[moduleName] || "模块成果")}</h3>${rawButton}</div>${summarizeModuleResult(moduleName, content)}`;
}

function summarizeModuleResult(moduleName, data) {
  if (!data) return `<div class="result-card empty"><h4>${esc(MODULE_RESULT_TITLES[moduleName] || "模块结果")}</h4><p>暂未生成关键结果文件。模块运行完成后会自动显示。</p></div>`;
  if (moduleName === "00_style_system") return summarizeStyle(data);
  if (moduleName === "01_novel_parser") return summarizeNovel(data);
  if (moduleName === "02_script_writer") return summarizeScript(data);
  if (moduleName === "03_character_system") return summarizeCharacters(data);
  if (moduleName === "04_scene_system") return summarizeScenes(data);
  if (moduleName === "05_prop_system") return summarizeProps(data);
  if (moduleName === "06_storyboard") return summarizeStoryboard(data);
  if (moduleName === "07_storyboard_image") return summarizeImages(data);
  if (moduleName === "08_audio") return summarizeAudio(data);
  if (moduleName === "09_video") return summarizeVideo(data);
  if (moduleName === "10_final_assembly") return summarizeFinal(data);
  return `<div class="result-card"><pre>${esc(JSON.stringify(data, null, 2).slice(0, 4000))}</pre></div>`;
}

function rMetric(label, value) {
  return `<div class="result-metric"><div class="rm-num">${esc(value)}</div><div class="rm-label">${esc(label)}</div></div>`;
}

function rChips(items, empty = "无") {
  const arr = (Array.isArray(items) ? items : []).filter(Boolean).slice(0, 12);
  if (!arr.length) return `<span class="muted">${esc(empty)}</span>`;
  return `<div class="result-chips">${arr.map((x) => `<span>${esc(typeof x === "string" ? x : JSON.stringify(x))}</span>`).join("")}</div>`;
}

function rTable(headers, rows) {
  if (!rows.length) return `<div class="muted">暂无明细</div>`;
  return `<div class="result-table-wrap"><table class="result-table"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function rGet(obj, paths, fallback = "") {
  for (const path of paths) {
    const value = path.split(".").reduce((cur, key) => (cur && cur[key] !== undefined ? cur[key] : undefined), obj);
    if (value !== undefined && value !== null && value !== "" && !(Array.isArray(value) && !value.length)) return value;
  }
  return fallback;
}

function rArr(v) { return Array.isArray(v) ? v : []; }
function rShort(v, n = 90) { const text = String(v ?? "").replace(/\s+/g, " ").trim(); return text.length > n ? text.slice(0, n) + "…" : text; }
function rCount(v) { return Array.isArray(v) ? v.length : 0; }
function rGenericArray(data, keys) { for (const key of keys) { const value = rGet(data, [key], null); if (Array.isArray(value)) return value; } return []; }

function summarizeStyle(data) {
  return `<div class="result-card"><h4>${esc(data.display_name || data.style_id || "当前风格")}</h4><p>${esc(data.core_style || "")}</p><div class="result-metrics">${rMetric("风格ID", data.style_id || "-")}${rMetric("视觉类型", data.visual_type || "-")}${rMetric("时代", data.era || "-")}</div><h5>镜头语言</h5>${rChips(data.camera_language)}<h5>光影色彩</h5>${rChips([...(data.lighting || []), ...(data.color_palette || [])])}</div>`;
}

function summarizeNovel(data) {
  const story = rGet(data, ["story_understanding", "story_summary", "summary", "core_story", "analysis.story_summary", "outputs.01A.story_understanding", "outputs.01A.summary"], "");
  const themes = rGet(data, ["themes", "theme", "story_themes", "outputs.01A.themes"], []);
  const events = rGenericArray(data, ["events", "event_graph.events", "story_events", "outputs.01C.events", "outputs.01C.event_graph.events"]);
  const candidates = [...rGenericArray(data, ["candidate_characters", "asset_candidates.characters", "outputs.01D.candidate_characters"]), ...rGenericArray(data, ["candidate_scenes", "asset_candidates.scenes", "outputs.01D.candidate_scenes"]), ...rGenericArray(data, ["candidate_props", "asset_candidates.props", "outputs.01D.candidate_props"])];
  return `<div class="result-card"><h4>故事理解</h4><p>${esc(story || "未找到摘要字段，可点击原始 JSON 查看完整结果。")}</p><div class="result-metrics">${rMetric("事件", rCount(events))}${rMetric("候选资产", rCount(candidates))}${rMetric("主题", Array.isArray(themes) ? themes.length : (themes ? 1 : 0))}</div><h5>主题/关键词</h5>${rChips(Array.isArray(themes) ? themes : [themes])}<h5>前几个事件</h5>${rTable(["事件", "说明"], events.slice(0, 8).map((e, i) => [esc(e.event_id || e.id || i + 1), esc(rShort(e.summary || e.event || e.description || e.text || JSON.stringify(e), 120))]))}</div>`;
}

function summarizeScript(data) {
  const lines = rGenericArray(data, ["voice_lines", "script_lines", "lines", "segments", "script.voice_lines"]);
  const acts = rGenericArray(data, ["acts", "structure.acts", "story_beats", "beats"]);
  const sample = lines.length ? lines : acts;
  return `<div class="result-card"><h4>剧本改编</h4><div class="result-metrics">${rMetric("台词/旁白行", rCount(lines))}${rMetric("结构段", rCount(acts))}${rMetric("状态", data.status || "-")}</div><h5>前几条内容</h5>${rTable(["序号", "角色/类型", "内容"], sample.slice(0, 10).map((x, i) => [esc(x.line_id || x.segment_id || i + 1), esc(x.speaker || x.character || x.line_type || x.type || ""), esc(rShort(x.text || x.content || x.dialogue || x.summary || JSON.stringify(x), 140))]))}</div>`;
}

function summarizeCharacters(data) {
  const chars = rArr(data.characters);
  return `<div class="result-card"><h4>角色库</h4><div class="result-metrics">${rMetric("角色", chars.length)}${rMetric("主资产", rCount(data.main_assets_for_06))}${rMetric("可选资产", rCount(data.optional_assets_for_06))}</div>${rTable(["角色", "性别", "身份", "外观/气质"], chars.slice(0, 12).map((c) => [esc(c.canonical_name || c.name || ""), esc(c.gender || ""), esc(rShort(c.identity || c.role_function || "", 50)), esc(rShort(c.appearance || c.temperament || "", 110))]))}</div>`;
}

function summarizeScenes(data) {
  const scenes = rArr(data.scenes);
  return `<div class="result-card"><h4>场景库</h4><div class="result-metrics">${rMetric("场景", scenes.length)}${rMetric("主场景", scenes.filter(s => s.asset_level === "main").length)}${rMetric("状态", data.status || "-")}</div>${rTable(["场景", "类型", "视觉描述"], scenes.slice(0, 12).map((s) => [esc(s.canonical_scene_name || s.name || ""), esc(s.scene_type || s.asset_level || ""), esc(rShort(s.visual_description || s.appearance || s.description || "", 130))]))}</div>`;
}

function summarizeProps(data) {
  const props = rArr(data.props);
  return `<div class="result-card"><h4>道具库</h4><div class="result-metrics">${rMetric("道具", props.length)}${rMetric("关键道具", props.filter(p => p.asset_level === "main" || p.importance === "key").length)}${rMetric("状态", data.status || "-")}</div>${rTable(["道具", "用途", "视觉描述"], props.slice(0, 12).map((p) => [esc(p.canonical_prop_name || p.name || ""), esc(rShort(p.role_function || p.usage || p.story_function || "", 60)), esc(rShort(p.visual_description || p.appearance || p.description || "", 130))]))}</div>`;
}

function summarizeStoryboard(data) {
  const frames = rArr(data.frames);
  return `<div class="result-card"><h4>分镜</h4><div class="result-metrics">${rMetric("分镜帧", frames.length)}${rMetric("四宫格组", rCount(data.four_grid_preview_groups))}${rMetric("出图造型需求", rCount(data.appearance_asset_requirements))}</div>${rTable(["序号", "场景", "人物", "动作/镜头"], frames.slice(0, 12).map((f) => { const scene = typeof f.scene === "object" ? f.scene.canonical_scene_name : f.scene; const chars = rArr(f.characters).map(c => c.canonical_name || c.name).filter(Boolean).join("、"); return [esc(f.sequence_index || f.frame_id || ""), esc(scene || ""), esc(chars || "无"), esc(rShort(`${f.story_action || ""} ${f.camera_plan || ""}`, 140))]; }))}</div>`;
}

function summarizeImages(data) {
  const manifest = data.image_manifest || data;
  const images = rArr(manifest.images || data.images);
  const done = images.filter(x => x.status === "success" || x.execution_mode === "dry_run").length;
  return `<div class="result-card"><h4>分镜图</h4><div class="result-metrics">${rMetric("图片任务", images.length)}${rMetric("完成/规划", done)}${rMetric("执行模式", data.execution_mode || manifest.execution_mode || "-")}</div>${rTable(["帧", "状态", "输出路径"], images.slice(0, 12).map((img) => [esc(img.frame_id || img.sequence_index || ""), esc(img.status || img.execution_mode || ""), esc(rShort(img.image_path || img.output_image_path || "", 90))]))}</div>`;
}

function summarizeAudio(data) {
  const entries = rArr(data.entries || data.lines || data.segments);
  return `<div class="result-card"><h4>音频时间线</h4><div class="result-metrics">${rMetric("音频段", entries.length)}${rMetric("总时长", data.duration_seconds || data.total_duration_seconds || "-")}${rMetric("状态", data.status || "-")}</div>${rTable(["时间", "角色/类型", "文本"], entries.slice(0, 12).map((e) => [esc(`${e.start_seconds ?? e.start ?? ""}-${e.end_seconds ?? e.end ?? ""}`), esc(e.speaker || e.character || e.line_type || e.type || ""), esc(rShort(e.text || e.content || "", 120))]))}</div>`;
}

function summarizeVideo(data) {
  const segments = rArr(data.segments || data.video_segments || data.video_manifest?.segments || data.outputs?.["09A"]?.segments);
  return `<div class="result-card"><h4>视频生成</h4><div class="result-metrics">${rMetric("视频段", segments.length)}${rMetric("状态", data.status || "-")}${rMetric("最终视频", data.final_video_ready === true ? "已生成" : "未生成")}</div>${rTable(["段", "状态", "输出"], segments.slice(0, 12).map((s) => [esc(s.segment_id || s.segment_index || ""), esc(s.status || s.execution_mode || ""), esc(rShort(s.output_clip_path || s.final_video_path || "", 100))]))}</div>`;
}

function summarizeFinal(data) {
  return `<div class="result-card"><h4>最终成片</h4><div class="result-metrics">${rMetric("状态", data.status || "-")}${rMetric("视频就绪", data.final_video_ready === true ? "是" : "否")}${rMetric("输出", data.final_video_path || data.final_path || "-")}</div><p>${esc(data.merge_note || data.note || data.message || "")}</p></div>`;
}

function renderReviewBox(moduleName) {
  const wrap = $("moduleReviewBox");
  if (!wrap || !moduleName) return;
  const key = `ai_drama_module_review_note:${state.currentSnapshot?.run_dir || "unknown"}:${moduleName}`;
  const saved = localStorage.getItem(key) || "";
  const label = mName(moduleName);
  wrap.innerHTML = `
    <h4>我对【${esc(label)}】的修改意见</h4>
    <div class="muted">写完意见后，可直接调用 LLM 修改当前模块产物。系统会先生成修正版 JSON，不会立刻覆盖原结果。</div>
    <textarea id="moduleReviewText" placeholder="例如：角色张捕头年龄不要写成中年；场景要更阴暗；第 5 个分镜动作太复杂，改成近景对峙。">${esc(saved)}</textarea>
    <div class="review-actions">
      <button class="btn small primary" id="llmRewriteBtn">调用 LLM 修改</button>
      <button class="btn small" id="saveReviewNoteBtn">保存意见</button>
      <button class="btn small ghost" id="clearReviewNoteBtn">清空</button>
    </div>
    <div id="reviewRewriteStatus" class="muted" style="margin-top:8px"></div>
  `;
  $("llmRewriteBtn")?.addEventListener("click", () => callLLMRewrite(moduleName));
  $("saveReviewNoteBtn")?.addEventListener("click", () => {
    localStorage.setItem(key, $("moduleReviewText")?.value || "");
    alert("已保存到本地浏览器。");
  });
  $("clearReviewNoteBtn")?.addEventListener("click", () => {
    localStorage.removeItem(key);
    const textarea = $("moduleReviewText");
    if (textarea) textarea.value = "";
  });
}

async function callLLMRewrite(moduleName) {
  const textarea = $("moduleReviewText");
  const status = $("reviewRewriteStatus");
  const note = textarea?.value?.trim() || "";
  const runDir = state.currentSnapshot?.run_dir || "";
  if (!runDir) return alert("请先选择或运行一个项目。");
  if (!note) return alert("请先填写修改意见。");
  localStorage.setItem(`ai_drama_module_review_note:${runDir}:${moduleName}`, note);
  if (status) status.innerHTML = "正在调用 LLM 修改当前模块产物，请稍候...";
  try {
    const result = await api("/api/review/rewrite", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_dir: runDir, module_name: moduleName, user_note: note }) });
    state.latestReviewedResult = result;
    if (status) {
      status.innerHTML = `<div style="color:var(--success);font-weight:800">LLM 已生成修正版，原始产物未覆盖。</div><div class="muted">修正版：${esc(result.reviewed_path || "")}</div><div class="review-actions" style="margin-top:8px"><button class="btn small" onclick="previewFile('${escAttr(result.reviewed_path || "")}')">预览修正版 JSON</button><button class="btn small primary" onclick="applyLatestReviewedResult()">应用修正版</button></div>`;
    }
    await previewFile(result.reviewed_path);
  } catch (err) {
    if (status) status.innerHTML = `<span style="color:var(--danger)">LLM 修改失败：${esc(String(err))}</span>`;
  }
}

async function applyLatestReviewedResult() {
  const result = state.latestReviewedResult;
  const moduleName = state.selectedModule;
  const runDir = state.currentSnapshot?.run_dir || "";
  if (!result?.reviewed_path) return alert("没有可应用的修正版。");
  if (!confirm("确定应用修正版吗？系统会覆盖当前模块正式产物，并自动保留备份。")) return;
  const status = $("reviewRewriteStatus");
  try {
    const applied = await api("/api/review/apply", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_dir: runDir, module_name: moduleName, reviewed_path: result.reviewed_path }) });
    if (status) {
      status.innerHTML = `<div style="color:var(--success);font-weight:800">已应用修正版。</div><div class="muted">覆盖目标：${esc(applied.target_path || "")}</div><div class="muted">备份文件：${esc(applied.backup_path || "")}</div>`;
    }
    await refreshAll();
    renderStageDetail();
  } catch (err) {
    if (status) status.innerHTML = `<span style="color:var(--danger)">应用失败：${esc(String(err))}</span>`;
  }
}

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
  if (moduleName === "01_novel_parser" || moduleName === "00_style_system") {
    hint.innerHTML = `<span style="color:var(--success)">✓ ${mName(moduleName)}无前置依赖，可单独运行</span>`;
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

function renderStylePicker() {
  const projectInput = $("projectIdInput");
  if (!projectInput || $("stylePresetInput")) return;
  const section = document.createElement("div");
  section.className = "sidebar-section";
  section.innerHTML = `<div class="sidebar-label">项目风格</div><select id="stylePresetInput"></select><div class="style-preset-hint">先选风格，再启动流程；后续 LLM 只接收该风格生成的 STYLE_BIBLE。</div>`;
  const currentSection = projectInput.closest(".sidebar-section");
  if (currentSection && currentSection.parentNode) {
    currentSection.parentNode.insertBefore(section, currentSection.nextSibling);
  }
  const select = $("stylePresetInput");
  const selected = localStorage.getItem(STYLE_STORAGE_KEY) || DEFAULT_STYLE;
  select.innerHTML = STYLE_PRESETS.map(([id, name]) => `<option value="${esc(id)}" ${id === selected ? "selected" : ""}>${esc(name)}｜${esc(id)}</option>`).join("");
  select.addEventListener("change", () => localStorage.setItem(STYLE_STORAGE_KEY, select.value));
}

function bindActions() {
  $("startFullBtn")?.addEventListener("click", () => startJob({ from_module: "00_style_system" }));
  $("startTextBtn")?.addEventListener("click", () => startJob({ from_module: "00_style_system", to_module: "06_storyboard", image_execution_mode: "dry_run", audio_execution_mode: "dry_run", video_execution_mode: "dry_run" }));
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

async function init() {
  renderStylePicker();
  bindActions();
  await loadPipeline();
  renderStepRunGrid();
  await refreshAll();
}

window.openProject = openProject;
window.selectModule = selectModule;
window.previewFile = previewFile;
window.previewTraceDir = previewTraceDir;
window.getPayload = getPayload;
window.runSingleModule = runSingleModule;
window.repairRunModule = repairRunModule;
window.repairRunFrom = repairRunFrom;
window.runHealthCheck = runHealthCheck;
window.applyLatestReviewedResult = applyLatestReviewedResult;

init().catch((err) => { console.error(err); if ($("liveLog")) $("liveLog").textContent = String(err); });
