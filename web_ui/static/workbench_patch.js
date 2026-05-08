(() => {
  function setActiveStageTab() {
    if (typeof window.switchTab === "function") {
      window.switchTab("stage");
      return;
    }
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "stage"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.toggle("active", c.id === "tabStage"));
  }

  function patchSelectModule() {
    if (!window.state || window.__workbenchSelectModulePatched) return;
    window.__workbenchSelectModulePatched = true;

    window.selectModule = async function patchedSelectModule(name) {
      window.state.selectedModule = name;
      setActiveStageTab();
      if (typeof window.renderStageDetail === "function") {
        await window.renderStageDetail();
      }
      if (typeof window.renderModuleReviewBox === "function") {
        window.renderModuleReviewBox(name);
      }
    };
  }

  function patchModuleNames() {
    if (window.MODULE_NAMES) {
      window.MODULE_NAMES["00_style_system"] = window.MODULE_NAMES["00_style_system"] || "风格圣经";
      window.MODULE_NAMES["00_main_controller"] = window.MODULE_NAMES["00_main_controller"] || "总控";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    patchModuleNames();
    patchSelectModule();
  });
  setTimeout(() => {
    patchModuleNames();
    patchSelectModule();
  }, 300);
})();
