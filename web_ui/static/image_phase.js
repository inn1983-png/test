(function () {
  function el(id) { return document.getElementById(id); }
  function esc(value) {
    return String(value ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  }
  function badge2(status) {
    if (typeof badge === "function") return badge(status);
    return `<span class="badge ${esc(status || "pending")}">${esc(status || "pending")}</span>`;
  }
  function mediaUrl(path) {
    if (!path) return "";
    const runDir = typeof currentRunDir === "function" ? currentRunDir() : "";
    const rel = String(path).replace(/\\/g, "/");
    if (rel.startsWith("workspace/")) return `/media/${rel}`;
    if (runDir && rel.startsWith(runDir)) return `/media/${rel}`;
    return `/media/${rel}`;
  }
  async function loadJson(relPath) {
    if (typeof loadJsonFromRun === "function") return loadJsonFromRun(relPath);
    const runDir = typeof currentRunDir === "function" ? currentRunDir() : "";
    if (!runDir) return null;
    try {
      const res = await fetch(`/api/file?path=${encodeURIComponent(`${runDir}/${relPath}`)}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.type === "json" ? data.content : null;
    } catch (_) {
      return null;
    }
  }
  function preview(path) {
    if (typeof previewFile === "function") previewFile(path);
  }
  function card(title, subtitle, imagePath, status, metaRows, jsonPath) {
    const image = imagePath
      ? `<img class="media-thumb" src="${mediaUrl(imagePath)}" onerror="this.parentElement.classList.add('placeholder');this.remove();" />`
      : `<div class="media-placeholder">暂无图片</div>`;
    return `
      <div class="media-card">
        <div class="media-card-head">
          <div>
            <div class="media-title">${esc(title || "未命名")}</div>
            <div class="media-subtitle">${esc(subtitle || "")}</div>
          </div>
          ${badge2(status || "pending")}
        </div>
        <div class="media-image">${image}</div>
        <div class="media-meta">
          ${(metaRows || []).map((row) => `<div><span>${esc(row[0])}</span><strong>${esc(row[1] ?? "-")}</strong></div>`).join("")}
        </div>
        <div class="card-actions">
          ${jsonPath ? `<button class="btn small" onclick="previewFile('${jsonPath}')">查看 JSON</button>` : ""}
          ${imagePath ? `<button class="btn small" onclick="previewFile('${imagePath}')">预览图片</button>` : ""}
          <button class="btn small primary" onclick="regenerateImage('${esc(title || "image") }')">局部重跑</button>
        </div>
      </div>
    `;
  }
  function summaryCard(label, value, hint) {
    return `<div class="panel mini-stat"><span>${esc(label)}</span><strong>${esc(value)}</strong><p>${esc(hint || "")}</p></div>`;
  }
  async function renderImagePhase(snap) {
    const summary = el("imagePhaseSummary");
    const lockGrid = el("characterLockGrid");
    const appGrid = el("appearanceGrid");
    const refGrid = el("referenceAssetGrid");
    const frameGrid = el("storyboardImageGrid");
    if (!summary || !lockGrid || !appGrid || !refGrid || !frameGrid) return;
    if (!snap) {
      summary.innerHTML = summaryCard("07 状态", "等待", "运行 07 后展示图片阶段");
      lockGrid.innerHTML = appGrid.innerHTML = refGrid.innerHTML = frameGrid.innerHTML = `<div class="muted">暂无 07 产物。</div>`;
      return;
    }
    const [locks, apps, refs, images, meta, dep] = await Promise.all([
      loadJson("07_storyboard_image/character_lock_manifest.json"),
      loadJson("07_storyboard_image/appearance_manifest.json"),
      loadJson("07_storyboard_image/reference_asset_manifest.json"),
      loadJson("07_storyboard_image/image_manifest.json"),
      loadJson("07_storyboard_image/storyboard_image_meta.json"),
      loadJson("07_storyboard_image/dependency_index.json"),
    ]);
    const lockRows = locks?.character_locks || [];
    const appRows = apps?.appearances || [];
    const sceneRows = refs?.scene_assets || [];
    const propRows = refs?.prop_assets || [];
    const imageRows = images?.images || [];
    const needsRetry = meta?.needs_retry ? "需要重跑" : "正常";
    summary.innerHTML = [
      summaryCard("定妆图", lockRows.length, "07A 文生图锁脸"),
      summaryCard("造型图", appRows.length, "07B 图生图换装"),
      summaryCard("参考资产", sceneRows.length + propRows.length, "07C 场景/道具"),
      summaryCard("分镜图", imageRows.length, `07D / ${needsRetry}`),
    ].join("");
    lockGrid.innerHTML = lockRows.length ? lockRows.map((item) => card(
      item.canonical_name,
      `${item.lock_key || ""} · 下游造型 ${Array.isArray(item.downstream_appearance_keys) ? item.downstream_appearance_keys.length : 0}`,
      item.selected_image_path,
      item.status,
      [["asset_level", item.asset_level], ["revision", item.revision], ["source frames", (item.source_frame_ids || []).length]],
      `${currentRunDir()}/07_storyboard_image/character_lock_manifest.json`
    )).join("") : `<div class="muted">暂无定妆图任务。</div>`;
    appGrid.innerHTML = appRows.length ? appRows.map((item) => card(
      item.appearance_asset_key,
      `${item.canonical_name || ""} · ${item.costume_id || ""}`,
      item.selected_image_path,
      item.status,
      [["base lock", item.base_lock_key], ["wearable", (item.wearable_props || []).join("，") || "无"], ["frames", (item.source_frame_ids || []).length]],
      `${currentRunDir()}/07_storyboard_image/appearance_manifest.json`
    )).join("") : `<div class="muted">暂无造型图任务。</div>`;
    const refRows = [...sceneRows.map((x) => ({ ...x, title: x.scene_key, kind: "scene" })), ...propRows.map((x) => ({ ...x, title: x.prop_key, kind: "prop" }))];
    refGrid.innerHTML = refRows.length ? refRows.map((item) => card(
      item.title,
      `${item.kind} reference`,
      item.selected_image_path,
      item.status,
      [["source mode", item.source_mode], ["revision", item.revision], ["frames", (item.source_frame_ids || []).length]],
      `${currentRunDir()}/07_storyboard_image/reference_asset_manifest.json`
    )).join("") : `<div class="muted">暂无场景/道具参考图任务。</div>`;
    frameGrid.innerHTML = imageRows.length ? imageRows.map((item) => card(
      item.frame_id,
      `第 ${item.sequence_index || "-"} 帧 · ${item.is_anchor_frame ? "锚点帧" : "普通帧"}`,
      item.image_path,
      item.status,
      [["scene", item.scene_ref_key], ["appearance", (item.appearance_asset_keys || []).join("，") || "无"], ["anchor", item.anchor_frame_id || "-"], ["prev", item.continuity_source_frame_id || "-"]],
      `${currentRunDir()}/07_storyboard_image/image_manifest.json`
    )).join("") : `<div class="muted">暂无分镜图任务。</div>`;
    if (dep && Object.keys(dep.frame_dependencies || {}).length) {
      summary.innerHTML += summaryCard("依赖图", Object.keys(dep.frame_dependencies || {}).length, "支持局部失效与重跑");
    }
  }
  window.renderImagePhase = renderImagePhase;

  const oldRenderSnapshot = window.renderSnapshot;
  if (typeof oldRenderSnapshot === "function") {
    window.renderSnapshot = async function () {
      await oldRenderSnapshot.apply(this, arguments);
      await renderImagePhase(window.state?.currentSnapshot || state?.currentSnapshot || null);
    };
  }

  const oldRefreshAll = window.refreshAll;
  if (typeof oldRefreshAll === "function") {
    window.refreshAll = async function () {
      await oldRefreshAll.apply(this, arguments);
      await renderImagePhase(window.state?.currentSnapshot || state?.currentSnapshot || null);
    };
  }

  setTimeout(() => {
    const startImage = el("startImagePhaseBtn");
    if (startImage && typeof startJob === "function") startImage.addEventListener("click", () => startJob({ only_module: "07_storyboard_image" }));
    const previewManifest = el("previewImageManifestBtn");
    if (previewManifest) previewManifest.addEventListener("click", () => { const rel = currentRunDir(); if (rel) preview(`${rel}/07_storyboard_image/image_manifest.json`); });
    const previewDep = el("previewDependencyBtn");
    if (previewDep) previewDep.addEventListener("click", () => { const rel = currentRunDir(); if (rel) preview(`${rel}/07_storyboard_image/dependency_index.json`); });
    const refresh = el("refreshBtn");
    if (refresh) refresh.addEventListener("click", () => renderImagePhase(window.state?.currentSnapshot || state?.currentSnapshot || null));
    renderImagePhase(window.state?.currentSnapshot || state?.currentSnapshot || null);
  }, 0);
})();
