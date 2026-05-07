// AI-NovelFlow inspired runtime workbench.
// Goal: make each pipeline module visible, highlight the active step, and expose outputs directly.
(function () {
  const MODULE_DISPLAY_NAMES = window.MODULE_DISPLAY_NAMES || {
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

  const moduleName = (name) => MODULE_DISPLAY_NAMES[name] || name || "未知模块";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const statusLabel = (status) => ({
    success: "完成",
    running: "运行中",
    failed: "失败",
    blocked: "阻塞",
    skipped: "跳过",
    pending: "等待",
    queued: "排队",
    not_started: "未开始",
    stopping: "停止中",
  }[status] || status || "未知");

  const statusBadge = (status) => {
    const cls = String(status || "pending").replace(/[^a-zA-Z0-9_-]/g, "");
    return `<span class="badge ${cls}">${statusLabel(status)}</span>`;
  };

  const keyOutputMap = {
    "00_main_controller": ["runtime_context.json", "manifest.json", "run_status.json", "00_data_link_check_report.json"],
    "01_novel_parser": ["novel_analysis.json"],
    "02_script_writer": ["script.json"],
    "03_character_system": ["characters.json"],
    "04_scene_system": ["scenes.json"],
    "05_prop_system": ["props.json"],
    "06_storyboard": ["storyboard.json", "storyboard_meta.json"],
    "07_storyboard_image": ["image_manifest.json", "image_meta.json"],
    "08_audio": ["final_audio.wav", "audio_timeline.json", "subtitle.srt", "subtitle.ass"],
    "09_video": ["video_manifest.json", "final_video.mp4"],
    "10_final_assembly": ["final.mp4", "final_manifest.json", "final_meta.json"],
  };

  function getState() {
    return window.state || {};
  }

  function currentRunDir() {
    const state = getState();
    return state.currentSnapshot?.run_dir || state.currentJob?.run_dir || "";
  }

  function findCurrentModule(modules) {
    const running = modules.find((item) => item.status === "running");
    if (running) return running.name;
    const failed = modules.find((item) => ["failed", "blocked"].includes(item.status));
    if (failed) return failed.name;
    const firstPending = modules.find((item) => ["pending", "queued"].includes(item.status));
    if (firstPending) return firstPending.name;
    return modules.at(-1)?.name || "00_main_controller";
  }

  function normalizeModules() {
    const state = getState();
    const snapshotModules = state.currentSnapshot?.modules;
    if (Array.isArray(snapshotModules) && snapshotModules.length) return snapshotModules;
    const displayPipeline = Array.isArray(state.displayPipeline) && state.displayPipeline.length
      ? state.displayPipeline
      : ["00_main_controller", ...(Array.isArray(state.pipeline) ? state.pipeline : [])];
    return displayPipeline.map((name) => ({
      name,
      status: "pending",
      message: name === "00_main_controller" ? "等待创建运行上下文 / 数据链路检查" : "等待运行",
      outputs: [],
      stages: [],
      quality: {},
    }));
  }

  function countIssues(module) {
    let count = 0;
    if (["failed", "blocked"].includes(module.status)) count += 1;
    for (const stage of module.stages || []) {
      if (stage.passed === false || Number(stage.issues_count || 0) > 0) count += Math.max(1, Number(stage.issues_count || 0));
    }
    const quality = module.quality || {};
    if (quality.needs_retry || quality.needs_review || quality.schema_validation_passed === false || quality.passed_all === false) count += 1;
    return count;
  }

  function getModuleOutputs(module) {
    const outputs = Array.isArray(module.outputs) ? module.outputs : [];
    const runDir = currentRunDir();
    const expected = keyOutputMap[module.name] || [];
    const expectedRows = expected.map((name) => {
      const path = module.name === "00_main_controller" ? `${runDir}/${name}` : `${runDir}/${module.name}/${name}`;
      const exists = outputs.some((item) => item.name === name || item.path === path);
      return { name, path, exists, expected: true };
    });
    const actualRows = outputs.map((item) => ({ ...item, exists: true, expected: false }));
    const merged = [...actualRows];
    for (const row of expectedRows) {
      if (!merged.some((item) => item.name === row.name || item.path === row.path)) merged.push(row);
    }
    return merged.slice(0, 8);
  }

  function ensureWorkbench() {
    let host = document.getElementById("nfWorkbench");
    if (host) return host;
    const dashboard = document.getElementById("view-dashboard");
    if (!dashboard) return null;
    host = document.createElement("section");
    host.id = "nfWorkbench";
    host.className = "nf-console";
    dashboard.insertBefore(host, dashboard.firstChild);
    return host;
  }

  function renderModuleCard(module, currentName) {
    const stages = module.stages || [];
    const outputs = getModuleOutputs(module);
    const issues = countIssues(module);
    const activeClass = module.name === currentName ? " active" : "";
    const outputButtons = outputs.filter((item) => item.exists && item.path).slice(0, 3).map((item) => (
      `<button onclick="window.previewFile && window.previewFile('${escapeHtml(item.path)}')">${escapeHtml(item.name)}</button>`
    )).join("");
    const fallbackPath = outputs.find((item) => item.path)?.path || "";
    return `
      <article class="nf-module-card ${escapeHtml(module.status || "pending")}${activeClass}" data-module="${escapeHtml(module.name)}">
        <div class="nf-card-top">
          <div>
            <div class="nf-card-name">${escapeHtml(moduleName(module.name))}</div>
            <div class="nf-card-raw">${escapeHtml(module.name)}</div>
          </div>
          ${statusBadge(module.status)}
        </div>
        <div class="nf-card-message">${escapeHtml(module.message || (module.name === currentName ? "当前关注步骤" : "等待阶段输出"))}</div>
        <div class="nf-card-stats">
          <div class="nf-stat"><span>阶段</span><strong>${stages.length}</strong></div>
          <div class="nf-stat"><span>产物</span><strong>${outputs.filter((item) => item.exists).length}</strong></div>
          <div class="nf-stat"><span>问题</span><strong>${issues}</strong></div>
        </div>
        <div class="nf-card-actions">
          ${outputButtons || (fallbackPath ? `<button onclick="window.previewFile && window.previewFile('${escapeHtml(fallbackPath)}')">查看预期产物</button>` : "")}
          <button onclick="window.nfWorkbenchRunOnly && window.nfWorkbenchRunOnly('${escapeHtml(module.name)}')">只跑这一步</button>
        </div>
      </article>`;
  }

  function renderOutputRows(modules, currentName) {
    const current = modules.find((item) => item.name === currentName) || modules[0];
    const outputs = getModuleOutputs(current);
    if (!outputs.length) return `<div class="muted">暂无输出。运行后这里会显示该步骤的 JSON、图片、音频或视频。</div>`;
    return outputs.map((item) => `
      <div class="nf-output-row">
        <div class="nf-output-main">
          <div class="nf-output-name">${item.exists ? "✅" : "○"} ${escapeHtml(item.name)}</div>
          <div class="nf-output-path">${escapeHtml(item.path || "")}</div>
        </div>
        ${item.exists && item.path ? `<button onclick="window.previewFile && window.previewFile('${escapeHtml(item.path)}')">预览</button>` : `<button disabled>未生成</button>`}
      </div>`).join("");
  }

  function renderMappingPanel() {
    const mapping = {
      image_workflow_mapping: {
        workflow_file: "AI_DRAMA_COMFYUI_WORKFLOW",
        mapping_file: "AI_DRAMA_COMFYUI_WORKFLOW_MAPPING",
        positive_node_id: "AI_DRAMA_COMFYUI_POSITIVE_NODE_ID 或 mapping.positive_prompt",
        negative_node_id: "AI_DRAMA_COMFYUI_NEGATIVE_NODE_ID 或 mapping.negative_prompt",
        output_prefix_node_id: "AI_DRAMA_COMFYUI_OUTPUT_PREFIX_NODE_ID 或 mapping.output_prefix",
        reference_images: "mapping.reference_image_nodes[]",
      },
      principle: "像 AI-NovelFlow 一样，工作流可换，代码只读 mapping，不把节点名写死。"
    };
    return `
      <div class="nf-mapping-box">
        <div>借鉴 AI-NovelFlow：ComfyUI 工作流不写死节点名，使用 mapping 注入。</div>
        <pre class="nf-mapping-code">${escapeHtml(JSON.stringify(mapping, null, 2))}</pre>
        <button class="nf-mapping-copy" onclick="navigator.clipboard && navigator.clipboard.writeText('${escapeHtml(JSON.stringify(mapping)).replace(/'/g, "&#39;")}')">复制映射模板</button>
      </div>`;
  }

  function renderWorkbench() {
    const host = ensureWorkbench();
    if (!host) return;
    const modules = normalizeModules();
    const currentName = findCurrentModule(modules);
    const current = modules.find((item) => item.name === currentName) || modules[0];
    host.innerHTML = `
      <div class="nf-console-header">
        <div>
          <div class="nf-console-title">NovelFlow 风格生产看板</div>
          <div class="nf-console-subtitle">每一步高亮显示、每一步展示阶段输出和关键产物。适合你现在调 01、02、07、08、09 时快速定位问题。</div>
        </div>
        <div class="nf-current-chip"><span class="nf-pulse"></span>当前步骤：${escapeHtml(moduleName(currentName))} · ${statusLabel(current?.status)}</div>
      </div>
      <div class="nf-module-grid">${modules.map((module) => renderModuleCard(module, currentName)).join("")}</div>
      <div class="nf-detail-grid">
        <div class="nf-detail-panel">
          <h3>当前步骤输出内容：${escapeHtml(moduleName(currentName))}</h3>
          ${renderOutputRows(modules, currentName)}
        </div>
        <div class="nf-detail-panel">
          <h3>ComfyUI 工作流映射提醒</h3>
          ${renderMappingPanel()}
        </div>
      </div>`;
  }

  async function runOnly(moduleName) {
    if (!window.getPayload) {
      alert("当前 UI 尚未初始化，不能启动单模块运行。");
      return;
    }
    const payload = window.getPayload({ only_module: moduleName });
    if (moduleName === "07_storyboard_image") payload.image_execution_mode = document.getElementById("imageExecutionModeInput")?.value || "dry_run";
    if (moduleName === "08_audio") payload.audio_execution_mode = document.getElementById("audioExecutionModeInput")?.value || "dry_run";
    if (moduleName === "09_video") payload.video_execution_mode = document.getElementById("videoExecutionModeInput")?.value || "dry_run";
    const res = await fetch("/api/jobs/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    const data = await res.json();
    if (window.state) {
      window.state.currentJob = data.job;
      window.state.logLines = [];
    }
    document.getElementById("liveLog").textContent = `只运行 ${moduleName}，等待输出...`;
    if (window.connectEvents) window.connectEvents(data.job.id);
  }

  window.nfWorkbenchRunOnly = runOnly;
  window.renderNovelFlowWorkbench = renderWorkbench;

  const originalRenderSnapshot = window.renderSnapshot;
  if (typeof originalRenderSnapshot === "function") {
    window.renderSnapshot = async function (...args) {
      const result = await originalRenderSnapshot.apply(this, args);
      renderWorkbench();
      return result;
    };
  }

  const originalLoadPipeline = window.loadPipeline;
  if (typeof originalLoadPipeline === "function") {
    window.loadPipeline = async function (...args) {
      const result = await originalLoadPipeline.apply(this, args);
      renderWorkbench();
      return result;
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    setTimeout(renderWorkbench, 200);
    setInterval(renderWorkbench, 1500);
  });
})();
