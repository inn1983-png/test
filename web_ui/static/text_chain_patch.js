(() => {
  // The original app.js button starts from 01_novel_parser and the server may
  // continue past 06. Override the click handler at capture phase so the user
  // friendly "文本链路 (00→06)" action actually runs the style-preconditioned
  // text chain only.
  function bindTextChainPatch() {
    const btn = document.getElementById("startTextBtn");
    if (!btn || btn.__textChainPatched) return;
    btn.__textChainPatched = true;
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      if (typeof window.startJob === "function") {
        window.startJob({
          from_module: "00_style_system",
          to_module: "06_storyboard",
          image_execution_mode: "dry_run",
          audio_execution_mode: "dry_run",
          video_execution_mode: "dry_run",
        });
      } else {
        alert("启动函数未就绪，请刷新页面后重试。");
      }
    }, true);
  }

  document.addEventListener("DOMContentLoaded", bindTextChainPatch);
  setTimeout(bindTextChainPatch, 300);
})();
