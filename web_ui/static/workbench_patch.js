(() => {
  let restoreTimer = null;
  let observerStarted = false;

  function setActiveStageTab() {
    if (typeof window.switchTab === "function") {
      window.switchTab("stage");
      return;
    }
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "stage"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.toggle("active", c.id === "tabStage"));
  }

  async function restoreWorkbench() {
    const moduleName = window.state?.selectedModule;
    const wrap = document.getElementById("stageDetail");
    if (!moduleName || !wrap || !window.state?.currentSnapshot) return;
    if (!wrap.querySelector("#moduleResultSummary") && typeof window.renderStageDetail === "function") {
      await window.renderStageDetail();
    }
    if (!wrap.querySelector("#moduleReviewBox") && typeof window.renderModuleReviewBox === "function") {
      window.renderModuleReviewBox(moduleName);
    }
  }

  function scheduleRestoreWorkbench() {
    if (restoreTimer) clearTimeout(restoreTimer);
    restoreTimer = setTimeout(() => {
      restoreWorkbench().catch(() => {});
    }, 80);
  }

  function observeStageDetail() {
    if (observerStarted) return;
    const wrap = document.getElementById("stageDetail");
    if (!wrap) return;
    observerStarted = true;
    const observer = new MutationObserver(() => {
      const moduleName = window.state?.selectedModule;
      if (!moduleName || !window.state?.currentSnapshot) return;
      if (!wrap.querySelector("#moduleResultSummary") || !wrap.querySelector("#moduleReviewBox")) {
        scheduleRestoreWorkbench();
      }
    });
    observer.observe(wrap, {childList: true, subtree: false});
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

  function initPatch() {
    patchModuleNames();
    patchSelectModule();
    observeStageDetail();
    scheduleRestoreWorkbench();
  }

  document.addEventListener("DOMContentLoaded", initPatch);
  setTimeout(initPatch, 300);
  setTimeout(initPatch, 1000);
})();
