(() => {
  const MODULE_RESULT_FILES = {
    "00_style_system": "style_bible.json",
    "01_novel_parser": "novel_analysis.json",
    "02_script_writer": "script.json",
    "03_character_system": "characters.json",
    "04_scene_system": "scenes.json",
    "05_prop_system": "props.json",
    "06_storyboard": "storyboard.json",
    "07_storyboard_image": "image_manifest.json",
    "08_audio": "audio_timeline.json",
    "09_video": "video_manifest.json",
    "10_final_assembly": "final_manifest.json",
  };

  const MODULE_RESULT_TITLES = {
    "00_style_system": "风格圣经",
    "01_novel_parser": "小说理解结果",
    "02_script_writer": "剧本改编结果",
    "03_character_system": "角色提取结果",
    "04_scene_system": "场景提取结果",
    "05_prop_system": "道具提取结果",
    "06_storyboard": "分镜结果",
    "07_storyboard_image": "图片生成结果",
    "08_audio": "音频结果",
    "09_video": "视频结果",
    "10_final_assembly": "成片结果",
  };

  const MAX_ITEMS = 12;
  const $id = (id) => document.getElementById(id);
  const htmlEsc = (v) => String(v ?? "").replace(/[&<>\"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));
  const attrEsc = (v) => htmlEsc(v).replace(/'/g, "&#39;");
  const appState = () => window.state || {};
  const appApi = (...args) => {
    if (typeof window.api !== "function") throw new Error("UI api bridge not ready");
    return window.api(...args);
  };
  const preview = (path) => {
    if (typeof window.previewFile === "function") return window.previewFile(path);
    alert(`预览功能未就绪：${path}`);
  };

  const get = (obj, paths, fallback = "") => {
    for (const path of paths) {
      const value = path.split(".").reduce((cur, key) => (cur && cur[key] !== undefined ? cur[key] : undefined), obj);
      if (value !== undefined && value !== null && value !== "" && !(Array.isArray(value) && !value.length)) return value;
    }
    return fallback;
  };
  const asArray = (v) => Array.isArray(v) ? v : [];
  const short = (v, n = 90) => {
    const text = String(v ?? "").replace(/\s+/g, " ").trim();
    return text.length > n ? text.slice(0, n) + "…" : text;
  };
  const count = (v) => Array.isArray(v) ? v.length : 0;

  function resultPath(moduleName) {
    const runDir = appState().currentSnapshot?.run_dir;
    const file = MODULE_RESULT_FILES[moduleName];
    if (!runDir || !file) return "";
    return `${runDir}/${moduleName}/${file}`;
  }

  async function fetchResultJson(moduleName) {
    const path = resultPath(moduleName);
    if (!path) return null;
    try {
      const data = await appApi(`/api/file?path=${encodeURIComponent(path)}`);
      if (data.type === "json") return {path, content: data.content};
      return {path, content: null};
    } catch (_) {
      return {path, content: null};
    }
  }

  function metric(label, value) {
    return `<div class="result-metric"><div class="rm-num">${htmlEsc(value)}</div><div class="rm-label">${htmlEsc(label)}</div></div>`;
  }

  function chips(items, empty = "无") {
    const arr = asArray(items).filter(Boolean).slice(0, MAX_ITEMS);
    if (!arr.length) return `<span class="muted">${htmlEsc(empty)}</span>`;
    return `<div class="result-chips">${arr.map((x) => `<span>${htmlEsc(typeof x === "string" ? x : JSON.stringify(x))}</span>`).join("")}</div>`;
  }

  function table(headers, rows) {
    if (!rows.length) return `<div class="muted">暂无明细</div>`;
    return `<div class="result-table-wrap"><table class="result-table"><thead><tr>${headers.map((h) => `<th>${htmlEsc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function genericArray(data, keys) {
    for (const key of keys) {
      const value = get(data, [key], null);
      if (Array.isArray(value)) return value;
    }
    return [];
  }

  function summarizeStyle(data) {
    return `<div class="result-card">
      <h4>${htmlEsc(data.display_name || data.style_id || "当前风格")}</h4>
      <p>${htmlEsc(data.core_style || "")}</p>
      <div class="result-metrics">${metric("风格ID", data.style_id || "-")}${metric("视觉类型", data.visual_type || "-")}${metric("时代", data.era || "-")}</div>
      <h5>镜头语言</h5>${chips(data.camera_language)}
      <h5>光影色彩</h5>${chips([...(data.lighting || []), ...(data.color_palette || [])])}
    </div>`;
  }

  function summarizeNovel(data) {
    const story = get(data, ["story_understanding", "story_summary", "summary", "core_story", "analysis.story_summary", "outputs.01A.story_understanding", "outputs.01A.summary"], "");
    const themes = get(data, ["themes", "theme", "story_themes", "outputs.01A.themes"], []);
    const events = genericArray(data, ["events", "event_graph.events", "story_events", "outputs.01C.events", "outputs.01C.event_graph.events"]);
    const candidates = [
      ...genericArray(data, ["candidate_characters", "asset_candidates.characters", "outputs.01D.candidate_characters"]),
      ...genericArray(data, ["candidate_scenes", "asset_candidates.scenes", "outputs.01D.candidate_scenes"]),
      ...genericArray(data, ["candidate_props", "asset_candidates.props", "outputs.01D.candidate_props"]),
    ];
    return `<div class="result-card"><h4>故事理解</h4><p>${htmlEsc(story || "未找到摘要字段，可点击原始 JSON 查看完整结果。")}</p><div class="result-metrics">${metric("事件", count(events))}${metric("候选资产", count(candidates))}${metric("主题", Array.isArray(themes) ? themes.length : (themes ? 1 : 0))}</div><h5>主题/关键词</h5>${chips(Array.isArray(themes) ? themes : [themes])}<h5>前几个事件</h5>${table(["事件", "说明"], events.slice(0, 8).map((e, i) => [htmlEsc(e.event_id || e.id || i + 1), htmlEsc(short(e.summary || e.event || e.description || e.text || JSON.stringify(e), 120))]))}</div>`;
  }

  function summarizeScript(data) {
    const lines = genericArray(data, ["voice_lines", "script_lines", "lines", "segments", "script.voice_lines"]);
    const acts = genericArray(data, ["acts", "structure.acts", "story_beats", "beats"]);
    const sample = lines.length ? lines : acts;
    return `<div class="result-card"><h4>剧本改编</h4><div class="result-metrics">${metric("台词/旁白行", count(lines))}${metric("结构段", count(acts))}${metric("状态", data.status || "-")}</div><h5>前几条内容</h5>${table(["序号", "角色/类型", "内容"], sample.slice(0, 10).map((x, i) => [htmlEsc(x.line_id || x.segment_id || i + 1), htmlEsc(x.speaker || x.character || x.line_type || x.type || ""), htmlEsc(short(x.text || x.content || x.dialogue || x.summary || JSON.stringify(x), 140))]))}</div>`;
  }

  function summarizeCharacters(data) {
    const chars = asArray(data.characters);
    return `<div class="result-card"><h4>角色库</h4><div class="result-metrics">${metric("角色", chars.length)}${metric("主资产", count(data.main_assets_for_06))}${metric("可选资产", count(data.optional_assets_for_06))}</div>${table(["角色", "性别", "身份", "外观/气质"], chars.slice(0, MAX_ITEMS).map((c) => [htmlEsc(c.canonical_name || c.name || ""), htmlEsc(c.gender || ""), htmlEsc(short(c.identity || c.role_function || "", 50)), htmlEsc(short(c.appearance || c.temperament || "", 110))]))}</div>`;
  }

  function summarizeScenes(data) {
    const scenes = asArray(data.scenes);
    return `<div class="result-card"><h4>场景库</h4><div class="result-metrics">${metric("场景", scenes.length)}${metric("主场景", scenes.filter(s => s.asset_level === "main").length)}${metric("状态", data.status || "-")}</div>${table(["场景", "类型", "视觉描述"], scenes.slice(0, MAX_ITEMS).map((s) => [htmlEsc(s.canonical_scene_name || s.name || ""), htmlEsc(s.scene_type || s.asset_level || ""), htmlEsc(short(s.visual_description || s.appearance || s.description || "", 130))]))}</div>`;
  }

  function summarizeProps(data) {
    const props = asArray(data.props);
    return `<div class="result-card"><h4>道具库</h4><div class="result-metrics">${metric("道具", props.length)}${metric("关键道具", props.filter(p => p.asset_level === "main" || p.importance === "key").length)}${metric("状态", data.status || "-")}</div>${table(["道具", "用途", "视觉描述"], props.slice(0, MAX_ITEMS).map((p) => [htmlEsc(p.canonical_prop_name || p.name || ""), htmlEsc(short(p.role_function || p.usage || p.story_function || "", 60)), htmlEsc(short(p.visual_description || p.appearance || p.description || "", 130))]))}</div>`;
  }

  function summarizeStoryboard(data) {
    const frames = asArray(data.frames);
    return `<div class="result-card"><h4>分镜</h4><div class="result-metrics">${metric("分镜帧", frames.length)}${metric("四宫格组", count(data.four_grid_preview_groups))}${metric("出图造型需求", count(data.appearance_asset_requirements))}</div>${table(["序号", "场景", "人物", "动作/镜头"], frames.slice(0, MAX_ITEMS).map((f) => { const scene = typeof f.scene === "object" ? f.scene.canonical_scene_name : f.scene; const chars = asArray(f.characters).map(c => c.canonical_name || c.name).filter(Boolean).join("、"); return [htmlEsc(f.sequence_index || f.frame_id || ""), htmlEsc(scene || ""), htmlEsc(chars || "无"), htmlEsc(short(`${f.story_action || ""} ${f.camera_plan || ""}`, 140))]; }))}</div>`;
  }

  function summarizeImages(data) {
    const manifest = data.image_manifest || data;
    const images = asArray(manifest.images || data.images);
    const done = images.filter(x => x.status === "success" || x.execution_mode === "dry_run").length;
    return `<div class="result-card"><h4>分镜图</h4><div class="result-metrics">${metric("图片任务", images.length)}${metric("完成/规划", done)}${metric("执行模式", data.execution_mode || manifest.execution_mode || "-")}</div>${table(["帧", "状态", "输出路径"], images.slice(0, MAX_ITEMS).map((img) => [htmlEsc(img.frame_id || img.sequence_index || ""), htmlEsc(img.status || img.execution_mode || ""), htmlEsc(short(img.image_path || img.output_image_path || "", 90))]))}</div>`;
  }

  function summarizeAudio(data) {
    const entries = asArray(data.entries || data.lines || data.segments);
    return `<div class="result-card"><h4>音频时间线</h4><div class="result-metrics">${metric("音频段", entries.length)}${metric("总时长", data.duration_seconds || data.total_duration_seconds || "-")}${metric("状态", data.status || "-")}</div>${table(["时间", "角色/类型", "文本"], entries.slice(0, MAX_ITEMS).map((e) => [htmlEsc(`${e.start_seconds ?? e.start ?? ""}-${e.end_seconds ?? e.end ?? ""}`), htmlEsc(e.speaker || e.character || e.line_type || e.type || ""), htmlEsc(short(e.text || e.content || "", 120))]))}</div>`;
  }

  function summarizeVideo(data) {
    const segments = asArray(data.segments || data.video_segments || data.video_manifest?.segments || data.outputs?.["09A"]?.segments);
    return `<div class="result-card"><h4>视频生成</h4><div class="result-metrics">${metric("视频段", segments.length)}${metric("状态", data.status || "-")}${metric("最终视频", data.final_video_ready === true ? "已生成" : "未生成")}</div>${table(["段", "状态", "输出"], segments.slice(0, MAX_ITEMS).map((s) => [htmlEsc(s.segment_id || s.segment_index || ""), htmlEsc(s.status || s.execution_mode || ""), htmlEsc(short(s.output_clip_path || s.final_video_path || "", 100))]))}</div>`;
  }

  function summarizeFinal(data) {
    return `<div class="result-card"><h4>最终成片</h4><div class="result-metrics">${metric("状态", data.status || "-")}${metric("视频就绪", data.final_video_ready === true ? "是" : "否")}${metric("输出", data.final_video_path || data.final_path || "-")}</div><p>${htmlEsc(data.merge_note || data.note || data.message || "")}</p></div>`;
  }

  function summarize(moduleName, data) {
    if (!data) return `<div class="result-card empty"><h4>${htmlEsc(MODULE_RESULT_TITLES[moduleName] || "模块结果")}</h4><p>暂未生成关键结果文件。模块运行完成后会自动显示。</p></div>`;
    if (moduleName === "00_style_system") return summarizeStyle(data);
    if (moduleName === "01_novel_parser") return summarizeNovel(data);
    if (moduleName === "02_script_writer") return summarizeScript(data);
    if (moduleName === "03_character_system") return summarizeCharacters(data);
    if (moduleName === "04_scene_system") return summarizeScenes(data);
    if (moduleName === "05_prop_system") return summarizeProps(data);
    if (moduleName === "06_storyboard") return summarizeStoryboard(data);
    if (moduleName === "07_storyboard_image") return summarizeImages(data);
    if (moduleName === "08_audio") return summarizeAudio(data);
    if (moduleName === "09_video") return summarizeVideo(data);
    if (moduleName === "10_final_assembly") return summarizeFinal(data);
    return `<div class="result-card"><pre>${htmlEsc(JSON.stringify(data, null, 2).slice(0, 4000))}</pre></div>`;
  }

  async function renderResultSummary(moduleName) {
    const wrap = $id("moduleResultSummary");
    if (!wrap) return;
    wrap.innerHTML = `<div class="result-loading">正在读取模块成果...</div>`;
    const result = await fetchResultJson(moduleName);
    const content = result?.content || null;
    const rawButton = result?.path ? `<button class="btn small ghost" onclick="window.previewFile ? previewFile('${attrEsc(result.path)}') : alert('预览未就绪')">查看原始 JSON</button>` : "";
    wrap.innerHTML = `<div class="result-header"><h3>${htmlEsc(MODULE_RESULT_TITLES[moduleName] || "模块成果")}</h3>${rawButton}</div>${summarize(moduleName, content)}`;
  }

  const originalRenderStageDetail = window.renderStageDetail;
  window.renderStageDetail = async function patchedRenderStageDetail(...args) {
    if (typeof originalRenderStageDetail === "function") {
      await originalRenderStageDetail.apply(this, args);
    }
    const wrap = $id("stageDetail");
    const moduleName = appState().selectedModule;
    if (!wrap || !moduleName || !appState().currentSnapshot) return;
    if (!MODULE_RESULT_FILES[moduleName]) return;
    if (!wrap.querySelector("#moduleResultSummary")) {
      wrap.insertAdjacentHTML("afterbegin", `<div id="moduleResultSummary" class="module-result-summary"></div>`);
    }
    await renderResultSummary(moduleName);
  };

  window.renderResultSummary = renderResultSummary;
  window.previewReviewedFile = preview;
})();
