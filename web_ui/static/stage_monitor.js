(() => {
  const MODULE_STAGES = {
    "01_novel_parser": ["01A", "01B", "01C", "01D", "01E"],
    "02_script_writer": ["02A", "02B", "02C", "02D", "02E"],
    "03_character_system": ["03A", "03B", "03C", "03D", "03E"],
    "04_scene_system": ["04A", "04B", "04C", "04D", "04E"],
    "05_prop_system": ["05A", "05B", "05C", "05D", "05E"],
    "06_storyboard": ["06A", "06B", "06C", "06D", "06E"],
    "07_storyboard_image": ["07A", "07B", "07C", "07D"],
    "08_audio": ["08A", "08B", "08C", "08D"],
    "09_video": ["09A", "09B", "09C", "09D"],
    "10_final_assembly": ["10A", "10B", "10C", "10D"],
  };

  const STAGE_HINTS = {
    "01A": ["原文结构解析", "结构解析", "novel structure"],
    "01B": ["候选角色/场景/道具提取", "候选资产", "candidate", "assets"],
    "01C": ["故事理解", "冲突梳理", "story understanding"],
    "01D": ["视觉风险", "高留存", "visual"],
    "01E": ["小说解析总检", "总检"],
    "02A": ["剧情拆解"], "02B": ["剧本初稿"], "02C": ["对白", "OS", "留白"], "02D": ["视觉动作链"], "02E": ["剧本总检"],
    "03A": ["角色归并"], "03B": ["角色资产卡"], "03C": ["剧本使用绑定"], "03D": ["角色库总检"], "03E": ["面向分镜复核"],
    "04A": ["场景归并"], "04B": ["场景资产卡"], "04C": ["剧本使用绑定"], "04D": ["场景库总检"], "04E": ["面向分镜复核"],
    "05A": ["道具归并"], "05B": ["道具资产卡"], "05C": ["剧本使用绑定"], "05D": ["道具库总检"], "05E": ["面向分镜复核"],
    "06A": ["资产闸门"], "06B": ["分镜规划"], "06C": ["单帧分镜生成"], "06D": ["连续性绑定"], "06E": ["分镜总检"],
    "07A": ["参考资产准备"], "07B": ["分镜图片任务"], "07C": ["ComfyUI", "图片执行"], "07D": ["图片总检"],
    "08A": ["音频队列"], "08B": ["音色情绪"], "08C": ["TTS"], "08D": ["混音字幕"],
    "09A": ["输入检查"], "09B": ["视频任务规划"], "09C": ["LTX", "视频执行"], "09D": ["视频总检"],
    "10A": ["输入检查"], "10B": ["视频准备"], "10C": ["音频字幕对齐"], "10D": ["最终导出"],
  };

  const stageRuntime = { activeStageId: "", activeModule: "", lastLogByStage: {}, outputCache: {} };
  const q = (id) => document.getElementById(id);
  const htmlEscape = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const attrEscape = (value) => htmlEscape(value).replace(/'/g, "&#39;");

  function getAppState() {
    try { return state || {}; } catch (_) { return window.state || {}; }
  }

  function getStageName(stageId) {
    try { if (typeof stageName === "function") return stageName(stageId); } catch (_) {}
    return stageId;
  }
  function getModuleName(moduleName) {
    try { if (typeof moduleName === "function") return moduleName(moduleName); } catch (_) {}
    return moduleName;
  }
  function getStatusLabel(status) {
    try { if (typeof statusLabel === "function") return statusLabel(status); } catch (_) {}
    return status || "等待";
  }

  function findStageFromLog(line) {
    const text = String(line || "");
    const direct = text.match(/\b(0[1-9]|10)[A-E]\b/i);
    if (direct) return direct[0].toUpperCase();
    for (const [stageId, hints] of Object.entries(STAGE_HINTS)) if (hints.some((hint) => text.includes(hint))) return stageId;
    return "";
  }

  function moduleForStage(stageId) {
    for (const [moduleName, stages] of Object.entries(MODULE_STAGES)) if (stages.includes(stageId)) return moduleName;
    return "";
  }

  function installLogHook() {
    const logBox = q("liveLog");
    if (!logBox || logBox.dataset.stageMonitorInstalled === "1") return;
    logBox.dataset.stageMonitorInstalled = "1";
    const observer = new MutationObserver(() => {
      const lines = String(logBox.textContent || "").split(/\r?\n/).filter(Boolean).slice(-30);
      for (const line of lines) {
        const stageId = findStageFromLog(line);
        if (!stageId) continue;
        stageRuntime.activeStageId = stageId;
        stageRuntime.activeModule = moduleForStage(stageId);
        stageRuntime.lastLogByStage[stageId] = line;
      }
      renderLiveStageBoard();
    });
    observer.observe(logBox, { childList: true, characterData: true, subtree: true });
  }

  function knownModules() {
    const appState = getAppState();
    const fromSnapshot = appState.currentSnapshot?.modules?.map((m) => m.name).filter(Boolean) || [];
    if (fromSnapshot.length) return fromSnapshot.filter((name) => MODULE_STAGES[name]);
    return Object.keys(MODULE_STAGES);
  }

  function stageOutputFromSnapshot(moduleName, stageId) {
    const appState = getAppState();
    const modules = appState.currentSnapshot?.modules || [];
    const module = modules.find((item) => item.name === moduleName);
    return (module?.stages || []).find((item) => String(item.stage_id || item.name || "").startsWith(stageId)) || null;
  }

  async function fetchStageOutputText(path) {
    if (!path) return "";
    if (stageRuntime.outputCache[path]) return stageRuntime.outputCache[path];
    try {
      const response = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
      if (!response.ok) return "";
      const data = await response.json();
      const text = data.type === "json" ? summarizeJson(data.content) : String(data.content || "").slice(0, 600);
      stageRuntime.outputCache[path] = text;
      return text;
    } catch (_) { return ""; }
  }

  function summarizeJson(content) {
    if (!content || typeof content !== "object") return JSON.stringify(content ?? "", null, 2).slice(0, 600);
    const quality = content.stage_quality || content.quality_report || {};
    const lines = [];
    if (content.stage || content.stage_id) lines.push(`阶段：${content.stage || content.stage_id}`);
    if (quality && typeof quality === "object") {
      if (quality.score !== undefined) lines.push(`评分：${quality.score}`);
      if (quality.passed !== undefined) lines.push(`通过：${quality.passed ? "是" : "否"}`);
      if (Array.isArray(quality.issues) && quality.issues.length) lines.push(`问题：${quality.issues.slice(0, 3).join("；")}`);
      if (Array.isArray(quality.revision_suggestions) && quality.revision_suggestions.length) lines.push(`修改建议：${quality.revision_suggestions.slice(0, 3).join("；")}`);
    }
    for (const key of ["summary", "story_understanding", "candidate_assets", "characters", "scenes", "props", "frames", "segments", "tasks", "result", "output"]) {
      const value = content[key];
      if (value === undefined) continue;
      const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
      lines.push(`${key}：${text.slice(0, 420)}`);
      if (lines.join("\n").length > 560) break;
    }
    return (lines.join("\n") || JSON.stringify(content, null, 2)).slice(0, 900);
  }

  function getStageClass(moduleName, stageId) {
    const appState = getAppState();
    const stage = stageOutputFromSnapshot(moduleName, stageId);
    const module = (appState.currentSnapshot?.modules || []).find((item) => item.name === moduleName);
    if (stageRuntime.activeStageId === stageId) return "stage-active";
    if (stage?.passed === false || module?.status === "failed") return "stage-failed";
    if (stage?.passed === true || stage?.path) return "stage-done";
    return "stage-pending";
  }

  function renderLiveStageBoard() {
    const board = q("liveStageBoard");
    if (!board) return;
    const appState = getAppState();
    board.innerHTML = knownModules().map((moduleName) => {
      const module = (appState.currentSnapshot?.modules || []).find((item) => item.name === moduleName) || {};
      const stages = MODULE_STAGES[moduleName] || [];
      return `<div class="live-stage-module"><div class="live-stage-module-title"><div><strong>${htmlEscape(getModuleName(moduleName))}</strong><div class="muted">${htmlEscape(moduleName)}</div></div><span class="badge ${htmlEscape(module.status || "pending")}">${htmlEscape(getStatusLabel(module.status || "pending"))}</span></div><div class="live-stage-cards">${stages.map((stageId) => renderStage(moduleName, stageId)).join("")}</div></div>`;
    }).join("");
    hydrateStageOutputs();
  }

  function renderStage(moduleName, stageId) {
    const stage = stageOutputFromSnapshot(moduleName, stageId);
    const cls = getStageClass(moduleName, stageId);
    const score = stage?.score ?? "-";
    const issues = stage?.issues_count ?? 0;
    const lastLog = stageRuntime.lastLogByStage[stageId] || "";
    const output = stage?.path ? `<div class="live-stage-output live-stage-empty" data-stage-path="${attrEscape(stage.path)}">读取阶段输出中...</div>` : `<div class="live-stage-output ${lastLog ? "" : "live-stage-empty"}">${htmlEscape(lastLog || "等待该阶段输出")}</div>`;
    return `<div class="live-stage-card ${cls}" data-stage-id="${stageId}"><div class="live-stage-id">${stageId}</div><div class="live-stage-name">${htmlEscape(getStageName(stageId))}</div><div class="live-stage-meta"><span class="live-stage-pill">评分 ${htmlEscape(score)}</span><span class="live-stage-pill">问题 ${htmlEscape(issues)}</span><span class="live-stage-pill">${cls === "stage-active" ? "正在运行" : cls === "stage-done" ? "已有输出" : cls === "stage-failed" ? "需处理" : "等待"}</span></div><div class="live-stage-output-title">阶段输出</div>${output}${stage?.path ? `<button class="btn small" onclick="previewFile('${attrEscape(stage.path)}')">打开完整输出</button>` : ""}</div>`;
  }

  async function hydrateStageOutputs() {
    const nodes = Array.from(document.querySelectorAll("[data-stage-path]"));
    for (const node of nodes) {
      const text = await fetchStageOutputText(node.dataset.stagePath);
      node.textContent = text || "该阶段文件已生成，但没有可摘要内容。";
      node.classList.toggle("live-stage-empty", !text);
    }
  }

  function patchRenderSnapshot() {
    try {
      const original = renderSnapshot;
      if (typeof original !== "function" || original.stageMonitorPatched) return;
      const patched = async function (...args) {
        const result = await original.apply(this, args);
        renderLiveStageBoard();
        return result;
      };
      patched.stageMonitorPatched = true;
      window.renderSnapshot = patched;
      renderSnapshot = patched;
    } catch (_) {}
  }

  function boot() { installLogHook(); patchRenderSnapshot(); renderLiveStageBoard(); }
  window.addEventListener("DOMContentLoaded", boot);
  window.renderLiveStageBoard = renderLiveStageBoard;
})();
