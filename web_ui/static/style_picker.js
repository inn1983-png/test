(() => {
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

  const STORAGE_KEY = "ai_drama_selected_style_preset";
  const DEFAULT_STYLE = "ancient_live_action_realistic";
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>\"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));

  function getSelectedStylePreset() {
    const el = $("stylePresetInput");
    return String(el?.value || localStorage.getItem(STORAGE_KEY) || DEFAULT_STYLE).trim() || DEFAULT_STYLE;
  }

  function renderStylePicker() {
    const projectInput = $("projectIdInput");
    if (!projectInput || $("stylePresetInput")) return;

    const section = document.createElement("div");
    section.className = "sidebar-section";
    section.innerHTML = `
      <div class="sidebar-label">项目风格</div>
      <select id="stylePresetInput"></select>
      <div class="style-preset-hint">先选风格，再启动流程；后续 LLM 只接收该风格生成的 STYLE_BIBLE。</div>
    `;

    const currentSection = projectInput.closest(".sidebar-section");
    if (currentSection && currentSection.parentNode) {
      currentSection.parentNode.insertBefore(section, currentSection.nextSibling);
    }

    const select = $("stylePresetInput");
    const selected = localStorage.getItem(STORAGE_KEY) || DEFAULT_STYLE;
    select.innerHTML = STYLE_PRESETS.map(([id, name]) => `<option value="${esc(id)}" ${id === selected ? "selected" : ""}>${esc(name)}｜${esc(id)}</option>`).join("");
    select.addEventListener("change", () => localStorage.setItem(STORAGE_KEY, select.value));
  }

  function patchFetchForStylePreset() {
    if (window.__stylePresetFetchPatched) return;
    window.__stylePresetFetchPatched = true;
    const originalFetch = window.fetch.bind(window);

    window.fetch = (input, init = {}) => {
      const url = typeof input === "string" ? input : String(input?.url || "");
      const method = String(init?.method || "GET").toUpperCase();
      const shouldPatch = method === "POST" && (
        url.includes("/api/jobs/start") ||
        url.includes("/api/system/check-data-link") ||
        url.includes("/api/system/self-check")
      );

      if (!shouldPatch || !init?.body || typeof init.body !== "string") {
        return originalFetch(input, init);
      }

      try {
        const payload = JSON.parse(init.body);
        const selectedStyle = getSelectedStylePreset();

        // UI only sends the selected style id. The full preset library is not sent
        // to downstream LLM stages. 00_style_system uses this id to generate one
        // STYLE_BIBLE, and LLM stages receive that STYLE_BIBLE as a precondition.
        payload.style_preset = selectedStyle;

        // Compatibility bridge for the current server env mapper. This is still
        // only the selected preset id, not a prompt suffix and not the style list.
        payload.image_style_suffix = selectedStyle;

        return originalFetch(input, {...init, body: JSON.stringify(payload)});
      } catch (_) {
        return originalFetch(input, init);
      }
    };
  }

  window.getSelectedStylePreset = getSelectedStylePreset;
  patchFetchForStylePreset();
  document.addEventListener("DOMContentLoaded", renderStylePicker);
})();
