(() => {
  const STORAGE_PREFIX = "ai_drama_module_review_note:";
  const $id = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>\"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));
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
      <div class="muted">这里先做用户可读复核和意见记录。写好后可以复制给返工提示词；后续可继续接入自动保存/自动返工接口。</div>
      <textarea id="moduleReviewText" placeholder="例如：角色张捕头年龄不要写成中年；场景要更阴暗；第 5 个分镜动作太复杂，改成近景对峙。">${esc(saved)}</textarea>
      <div class="review-actions">
        <button class="btn small primary" id="saveReviewNoteBtn">保存意见</button>
        <button class="btn small" id="copyReviewNoteBtn">复制返工意见</button>
        <button class="btn small ghost" id="clearReviewNoteBtn">清空</button>
      </div>
    `;
    const summary = wrap.querySelector("#moduleResultSummary");
    if (summary) summary.insertAdjacentElement("afterend", box);
    else wrap.insertAdjacentElement("afterbegin", box);

    $id("saveReviewNoteBtn")?.addEventListener("click", () => {
      localStorage.setItem(key, $id("moduleReviewText")?.value || "");
      alert("已保存到本地浏览器。刷新页面也会保留。");
    });
    $id("copyReviewNoteBtn")?.addEventListener("click", async () => {
      const note = $id("moduleReviewText")?.value || "";
      const text = `【返工模块】${moduleNameValue} / ${label}\n\n【用户修改意见】\n${note}\n\n【要求】请在不破坏上游数据结构和当前项目风格圣经的前提下，根据以上意见重写/修正该模块产物。`;
      await copyText(text);
      alert("已复制返工意见。可粘贴到返工提示词或手动修改环节。");
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
})();
