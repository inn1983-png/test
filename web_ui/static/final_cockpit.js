(() => {
  const MODULE_ORDER = [
    "00_main_controller",
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
  ];

  const OUTPUT_PRIORITY = [
    "01_novel_parser/novel_analysis.json",
    "02_script_writer/script.json",
    "03_character_system/characters.json",
    "04_scene_system/scenes.json",
    "05_prop_system/props.json",
    "06_storyboard/storyboard.json",
    "07_storyboard_image/image_manifest.json",
    "08_audio/final_audio.wav",
    "08_audio/subtitle.srt",
    "09_video/video_manifest.json",
    "09_video/final_video.mp4",
    "10_final_assembly/final.mp4",
    "10_final_assembly/final_manifest.json",
  ];

  const q = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const attr = (value) => esc(value).replace(/'/g, "&#39;");

  function appState() {
    try { return state || {}; } catch (_) { return window.state || {}; }
  }

  function labelModule(name) {
    try { if (typeof moduleName === "function") return moduleName(name); } catch (_) {}
    return name;
  }

  function labelStatus(status) {
    try { if (typeof statusLabel === "function") return statusLabel(status); } catch (_) {}
    return status || "等待";
  }

  function snap() {
    return appState().currentSnapshot || null;
  }

  function modules() {
    return snap()?.modules || [];
  }

  function importantOutputs() {
    return snap()?.important_outputs || [];
  }

  function moduleByName(name) {
    return modules().find((m) => m.name === name) || {};
  }

  function failedModule() {
    return modules().find((m) => ["failed", "blocked"].includes(m.status));
  }

  function runningModule() {
    return modules().find((m) => m.status === "running");
  }

  function nextPendingModule() {
    return modules().find((m) => ["pending", "not_started", undefined, null, ""].includes(m.status));
  }

  function successCount() {
    return modules().filter((m) => ["success", "skipped"].includes(m.status)).length;
  }

  function issueCount() {
    return modules().reduce((sum, m) => {
      const stageIssues = (m.stages || []).reduce((s, st) => s + Number(st.issues_count || 0) + (st.passed === false ? 1 : 0), 0);
      return sum + stageIssues + (["failed", "blocked"].includes(m.status) ? 1 : 0);
    }, 0);
  }

  function actionPlan() {
    const s = snap();
    const fm = failedModule();
    const rm = runningModule();
    const pm = nextPendingModule();
    if (!s) return { kind: "idle", title: "先创建或选择项目", detail: "粘贴小说正文，设置 project_id，然后启动小说解析或全流程。", module: "01_novel_parser", button: "启动小说解析" };
    if (fm) return { kind: "failed", title: `先处理 ${labelModule(fm.name)} 的失败`, detail: fm.message || "该模块失败或阻塞。建议先查看阶段输出和返工中心，再从该模块继续运行。", module: fm.name, button: "从失败模块继续跑" };
    if (rm) return { kind: "running", title: `${labelModule(rm.name)} 正在运行`, detail: "当前不建议重复启动。请观察制作指挥台的高亮阶段和右侧当前节点输出。", module: rm.name, button: "查看分步输出" };
    if (s.summary_status === "success") return { kind: "success", title: "全链路已完成", detail: "可以在产物中心查看 final.mp4、字幕、manifest，也可以单独重跑图片、音频或视频模块做精修。", module: "10_final_assembly", button: "查看最终产物" };
    if (pm) return { kind: "pending", title: `下一步：运行 ${labelModule(pm.name)}`, detail: "上游模块已有部分产物。建议从等待模块继续，而不是从头重跑。", module: pm.name, button: "运行下一模块" };
    return { kind: "review", title: "检查产物和返工中心", detail: "没有检测到正在运行或失败模块。请检查关键产物是否满足生产要求。", module: "00_main_controller", button: "查看产物中心" };
  }

  function renderOperatorConsole() {
    const root = q("operatorConsole");
    if (!root) return;
    const s = snap();
    const plan = actionPlan();
    const total = modules().length || MODULE_ORDER.length;
    const done = successCount();
    root.innerHTML = `<div class="operator-console">
      <section class="operator-panel">
        <div class="operator-head">
          <div><div class="operator-title">项目总览</div><div class="operator-desc">把当前项目的进度、问题、产物和下一步集中到一屏。</div></div>
          <span class="badge ${esc(s?.summary_status || "pending")}">${esc(labelStatus(s?.summary_status || "pending"))}</span>
        </div>
        <div class="operator-grid">
          <div class="operator-stat"><span>运行目录</span><strong>${esc(s?.run_dir || appState().currentJob?.run_dir || "未选择")}</strong></div>
          <div class="operator-stat"><span>模块完成</span><strong>${done}/${total}</strong></div>
          <div class="operator-stat"><span>问题数量</span><strong>${issueCount()}</strong></div>
        </div>
        <div class="health-lane">${renderHealthLane()}</div>
      </section>
      <section class="operator-panel">
        <div class="next-action-card">
          <div class="next-action-label">NEXT BEST ACTION</div>
          <div class="next-action-title">${esc(plan.title)}</div>
          <div class="next-action-detail">${esc(plan.detail)}</div>
          <div class="operator-actions">${renderActionButtons(plan)}</div>
        </div>
      </section>
    </div>
    <section class="operator-panel">
      <div class="operator-head"><div><div class="operator-title">关键产物快捷入口</div><div class="operator-desc">不用翻 workspace 文件夹，常用 JSON、音频、字幕、视频都在这里打开。</div></div><button class="btn small" onclick="switchView('outputs')">产物中心</button></div>
      <div class="artifact-quick-list">${renderArtifacts()}</div>
    </section>`;
  }

  function renderHealthLane() {
    const mods = modules().length ? modules() : MODULE_ORDER.map((name) => ({ name, status: "pending" }));
    return mods.map((m) => `<div class="health-dot-card"><div class="health-dot ${esc(m.status || "pending")}"></div><span>${esc(labelModule(m.name))}</span></div>`).join("");
  }

  function renderActionButtons(plan) {
    if (plan.kind === "running") return `<button class="btn small primary" onclick="switchView('stages')">查看分步输出</button><button class="btn small ghost" onclick="switchView('outputs')">查看产物</button>`;
    if (plan.kind === "success") return `<button class="btn small primary" onclick="switchView('outputs')">查看最终产物</button><button class="btn small" onclick="startJob({only_module:'07_storyboard_image',from_module:''})">精修分镜图</button>`;
    if (plan.kind === "failed") return `<button class="btn small primary" onclick="startJob({from_module:'${attr(plan.module)}',only_module:''})">从这里继续跑</button><button class="btn small danger" onclick="switchView('retry')">查看返工中心</button>`;
    if (plan.kind === "pending") return `<button class="btn small primary" onclick="startJob({only_module:'${attr(plan.module)}',from_module:''})">运行下一模块</button><button class="btn small" onclick="startJob({from_module:'${attr(plan.module)}',only_module:''})">从这里跑到结尾</button>`;
    return `<button class="btn small primary" onclick="startJob({only_module:'01_novel_parser',from_module:''})">启动小说解析</button><button class="btn small" onclick="switchView('runner')">打开生产控制台</button>`;
  }

  function renderArtifacts() {
    const outputs = importantOutputs();
    if (!outputs.length) return `<div class="operator-empty">暂无关键产物。运行 01 小说解析后会开始出现 JSON 输出；运行 10 后会出现 final.mp4。</div>`;
    const ordered = [...outputs].sort((a, b) => {
      const ai = OUTPUT_PRIORITY.findIndex((x) => a.path.endsWith(x));
      const bi = OUTPUT_PRIORITY.findIndex((x) => b.path.endsWith(x));
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    });
    return ordered.slice(0, 18).map((o) => `<div class="artifact-quick-item"><div><div class="artifact-quick-name">${esc(o.name)}</div><div class="artifact-quick-path">${esc(o.path)}</div></div><button class="btn small" onclick="previewFile('${attr(o.path)}')">打开</button></div>`).join("");
  }

  function patchRenderSnapshot() {
    try {
      const original = renderSnapshot;
      if (typeof original !== "function" || original.finalCockpitPatched) return;
      const patched = async function (...args) {
        const result = await original.apply(this, args);
        renderOperatorConsole();
        return result;
      };
      patched.finalCockpitPatched = true;
      window.renderSnapshot = patched;
      renderSnapshot = patched;
    } catch (_) {}
  }

  function boot() {
    patchRenderSnapshot();
    renderOperatorConsole();
  }

  window.addEventListener("DOMContentLoaded", boot);
  window.renderOperatorConsole = renderOperatorConsole;
})();
