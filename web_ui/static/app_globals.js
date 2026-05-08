(() => {
  // app.js uses top-level const/function declarations. Later UI plugins need a
  // stable window bridge, but we do not want to rewrite the whole app.js file.
  try {
    if (typeof state !== "undefined") window.state = state;
    if (typeof MODULE_NAMES !== "undefined") window.MODULE_NAMES = MODULE_NAMES;
    if (typeof STAGE_NAMES !== "undefined") window.STAGE_NAMES = STAGE_NAMES;
    if (typeof api !== "undefined") window.api = api;
    if (typeof previewFile !== "undefined") window.previewFile = previewFile;
    if (typeof switchTab !== "undefined") window.switchTab = switchTab;
    if (typeof renderStageDetail !== "undefined") window.renderStageDetail = renderStageDetail;
    if (typeof refreshAll !== "undefined") window.refreshAll = refreshAll;
    if (typeof renderPipeline !== "undefined") window.renderPipeline = renderPipeline;
    if (typeof renderRepairCenter !== "undefined") window.renderRepairCenter = renderRepairCenter;
  } catch (_) {}
})();
