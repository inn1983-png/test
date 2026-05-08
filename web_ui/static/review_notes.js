(() => {
  const STORAGE_PREFIX = "ai_drama_module_review_note:";
  const $id = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>\"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));
  const escAttr = (v) => esc(v).replace(/'/g, "&#39;");
  const moduleName = (n) => (window.MODULE_NAMES && window.MODULE_NAMES[n]) || n || "模块";

  function noteKey(moduleName) {
    const runDir = window.state?.currentSnapshot?.run_dir || "unknown_run";
    return `${STORAGE_PREFIX}${runDir}:${moduleName}`;
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
    return Promise.resolve();
  }

  async function postJson(path, payload) {
    const res = await fetch(path, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.status === "failed") throw new Error(data.error || JSON.stringify(data));
    return data;
  }

  async function callLLMRewrite(moduleNameValue) {
    const textarea = $id("moduleReviewText");
    const status = $id("reviewRewriteStatus");
    const note = textarea?.value?.trim() || "";
    const runDir = window.state?.currentSnapshot?.run_dir || "";
    if (!runDir) return alert("请先选择或运行一个项目。缺少 run_dir。 ");
    if (!moduleNameValue) return alert("请先点击一个模块。 ");
    if (!note) return alert("请先填写修改意见。 ");

    localStorage.setItem(noteKey(moduleNameValue), note);
    if (status) status.innerHTML = "正在调用 LLM 修改当前模块产物，请稍候...";
    try {
      const result = await postJson("/api/review/rewrite", {
        run_dir: runDir,
        module_name: moduleNameValue,
        user_note: note,
      });
      window.__latestReviewedResult = result;
      if (status) {
        status.innerHTML = `
          <div style="color:var(--success);font-weight:800">LLM 已生成修正版，原始产物未覆盖。</div>
          <div class="muted">修正版：${esc(result.reviewed_path || "")}</div>
          <div class="review-actions" style="margin-top:8px">
            <button class="btn small" onclick="previewFile('${escAttr(result.reviewed_path || "")}')">预览修正版 JSON</button>
            <button class="btn small primary" onclick="applyLatestReviewedResult()">应用修正版</button>
          </div>
        `;
      }
      await previewFile(result.reviewed_path);
    } catch (err) {
      if (status) status.innerHTML = `<span style="color:var(--danger)">LLM 修改失败：${esc(String(err))}</span>`;
    }
  }

  async function applyLatestReviewedResult() {
    const result = window.__latestReviewedResult;
    const moduleNameValue = window.state?.selectedModule;
    const runDir = window.state?.currentSnapshot?.run_dir || "";
    if (!result?.reviewed_path) return alert("没有可应用的修正版。 ");
    if (!confirm("确定应用修正版吗？系统会覆盖当前模块正式产物，并自动保留备份。")) return;
    const status = $id("reviewRewriteStatus");
    try {
      const applied = await postJson("/api/review/apply", {
        run_dir: runDir,
        module_name: moduleNameValue,
        reviewed_path: result.reviewed_path,
      });
      if (status) {
        status.innerHTML = `
          <div style="color:var(--success);font-weight:800">已应用修正版。</div>
          <div class="muted">覆盖目标：${esc(applied.target_path || "")}</div>
          <div class="muted">备份文件：${esc(applied.backup_path || "")}</div>
        `;
      }
      if (window.refreshAll) await window.refreshAll();
      if (window.renderStageDetail) await window.renderStageDetail();
    } catch (err) {
      if (status) status.innerHTML = `<span style="color:var(--danger)">应用失败：${esc(String(err))}</span>`;
    }
  }

  function renderReviewBox(moduleNameValue) {
    const wrap = $id("stageDetail");
    if (!wrap || !moduleNameValue) return;
    if (wrap.querySelector("#moduleReviewBox")) return;
    const key = noteKey(moduleNameValue);
    const saved = localStorage.getItem(key) || "";
    const label = moduleName(moduleNameValue);
    const box = document.createElement("div");
    box.id = "moduleReviewBox";
    box.className = "review-box";
    box.innerHTML = `
      <h4>我对【${esc(label)}】的修改意见</h4>
      <div class="muted">写完意见后，可直接调用 LLM 修改当前模块产物。系统会先生成修正版 JSON，不会立刻覆盖原结果。</div>
      <textarea id="moduleReviewText" placeholder="例如：角色张捕头年龄不要写成中年；场景要更阴暗；第 5 个分镜动作太复杂，改成近景对峙。">${esc(saved)}</textarea>
      <div class="review-actions">
        <button class="btn small primary" id="llmRewriteBtn">调用 LLM 修改</button>
        <button class="btn small" id="saveReviewNoteBtn">保存意见</button>
        <button class="btn small ghost" id="copyReviewNoteBtn">复制意见</button>
        <button class="btn small ghost" id="clearReviewNoteBtn">清空</button>
      </div>
      <div id="reviewRewriteStatus" class="muted" style="margin-top:8px"></div>
    `;
    const summary = wrap.querySelector("#moduleResultSummary");
    if (summary) summary.insertAdjacentElement("afterend", box);
    else wrap.insertAdjacentElement("afterbegin", box);

    $id("llmRewriteBtn")?.addEventListener("click", () => callLLMRewrite(moduleNameValue));
    $id("saveReviewNoteBtn")?.addEventListener("click", () => {
      localStorage.setItem(key, $id("moduleReviewText")?.value || "");
      alert("已保存到本地浏览器。刷新页面也会保留。");
    });
    $id("copyReviewNoteBtn")?.addEventListener("click", async () => {
      const note = $id("moduleReviewText")?.value || "";
      const text = `【返工模块】${moduleNameValue} / ${label}\n\n【用户修改意见】\n${note}\n\n【要求】请在不破坏上游数据结构和当前项目风格圣经的前提下，根据以上意见重写/修正该模块产物。`;
      await copyText(text);
      alert("已复制修改意见。 ");
    });
    $id("clearReviewNoteBtn")?.addEventListener("click", () => {
      localStorage.removeItem(key);
      const textarea = $id("moduleReviewText");
      if (textarea) textarea.value = "";
    });
  }

  const previousRender = window.renderStageDetail;
  if (typeof previousRender === "function") {
    window.renderStageDetail = async function reviewPatchedRenderStageDetail(...args) {
      await previousRender.apply(this, args);
      renderReviewBox(window.state?.selectedModule);
    };
  }

  window.renderModuleReviewBox = renderReviewBox;
  window.applyLatestReviewedResult = applyLatestReviewedResult;
})();
