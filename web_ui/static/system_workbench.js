(function () {
  const SYSTEMS = [
    { id: '00_main_controller', nav: '总控系统', title: '总控系统', kind: 'control', desc: '负责流程校验、运行上下文、数据链路、自检和模块调度。', stages: [
      ['流程校验', '检查 pipeline 顺序和模块契约。'],
      ['运行上下文', '创建项目、书籍、章节的工作区。'],
      ['依赖检查', '检查上游产物是否存在。'],
      ['运行调度', '执行 dry-run、单模块运行或范围运行。']
    ]},
    { id: '01_novel_parser', nav: '小说解析', title: '小说解析系统', kind: 'llm', desc: '真实 LLM 分阶段解析小说，输出小说理解、段落、事件、候选资产和生产预测。', stages: [
      ['故事理解', '理解世界观、主线、冲突、人物关系。'],
      ['段落拆分', '锁定原文段落边界，避免后续改写原文。'],
      ['事件图谱', '整理事件、冲突、高留存片段。'],
      ['候选资产提取', '提取所有角色、场景、道具候选。'],
      ['生产预测', '预测语音线、视频单元、情绪曲线。'],
      ['总检评分', '综合评分、修改意见、是否触发重跑。']
    ]},
    { id: '02_script_writer', nav: '剧本改编', title: '剧本改编系统', kind: 'llm', desc: '把小说解析结果改成对白、旁白、心理 OS 和留白结构。', stages: [
      ['剧情拆解', '拆出适合短剧的剧情单元。'],
      ['剧本初稿', '生成对白、旁白、心理 OS 和留白。'],
      ['节奏优化', '优化对白刺激和口播节奏。'],
      ['视觉动作链', '绑定动作、情绪、画面锚点。'],
      ['剧本总检', '检查可配音、可分镜、外观变化。']
    ]},
    { id: '03_character_system', nav: '角色库', title: '角色库系统', kind: 'llm', desc: '角色合并、角色卡、服装版本、定妆需求。', stages: [['角色归并','合并别名和称谓。'],['角色资产卡','输出角色外观和服装版本。'],['剧本绑定','绑定角色在剧本里的使用。'],['角色总检','检查拆角、漏角、变脸风险。'],['分镜复核','检查分镜是否可直接引用角色。']]},
    { id: '04_scene_system', nav: '场景库', title: '场景库系统', kind: 'llm', desc: '场景合并、分级、父子场景和参考图计划。', stages: [['场景归并','合并同一地点。'],['场景资产卡','输出场景等级和参考图需求。'],['剧本绑定','绑定使用段落。'],['场景总检','检查主场景和子场景。'],['分镜复核','检查分镜是否可引用。']]},
    { id: '05_prop_system', nav: '道具库', title: '道具库系统', kind: 'llm', desc: '道具合并、穿戴策略、关键道具参考图计划。', stages: [['道具归并','合并别名道具。'],['道具资产卡','输出道具类型和穿戴策略。'],['剧本绑定','绑定角色、服装和剧情。'],['道具总检','检查漏道具和误分类。'],['分镜复核','检查分镜是否可引用。']]},
    { id: '06_storyboard', nav: '单帧分镜', title: '单帧分镜系统', kind: 'llm', desc: '资产闸门、单帧分镜、连续性绑定。', stages: [['资产闸门','检查剧本、角色库、场景库、道具库是否齐全。'],['分镜规划','规划帧数和节奏。'],['单帧分镜','输出每帧动作、构图和资产引用。'],['连续性绑定','绑定前后帧衔接。'],['分镜总检','检查资产引用和连续性。']]},
    { id: '07_storyboard_image', nav: '分镜图', title: '分镜图系统', kind: 'image', desc: '参考资产准备、图片任务、ComfyUI 或 dry-run 执行。', stages: [['参考资产准备','准备角色、场景、道具参考。'],['图片任务构建','生成每帧图片任务。'],['图片执行','调用 ComfyUI 或 dry-run。'],['图片总检','输出失败帧和重跑计划。']]},
    { id: '08_audio', nav: '音频配音', title: '音频配音系统', kind: 'audio', desc: '对白、旁白、心理 OS、留白的配音、字幕和时间线。', stages: [['音频队列','构建配音文本队列。'],['音色情绪绑定','绑定说话人、音色和情绪。'],['配音执行','调用 TTS 或 dry-run。'],['混音字幕','输出最终音频、字幕和时间线。']]},
    { id: '09_video', nav: '视频生成', title: '视频生成系统', kind: 'video', desc: '按音频和分镜图生成视频片段。', stages: [['输入检查','检查分镜图和音频。'],['视频规划','规划片段和时长。'],['视频执行','调用视频模型或 dry-run。'],['视频总检','输出视频清单和问题。']]},
    { id: '10_final_assembly', nav: '最终合成', title: '最终合成系统', kind: 'assembly', desc: '拼接视频、对齐音频字幕、导出最终成片。', stages: [['输入检查','检查音频和视频片段。'],['视频准备','准备片段列表。'],['音频字幕对齐','对齐音频和字幕。'],['最终导出','导出最终视频。']]}
  ];

  function appState() {
    try { return state || {}; } catch (_) { return window.state || {}; }
  }

  function runDirNow() {
    const s = appState();
    return s.currentSnapshot?.run_dir || s.currentJob?.run_dir || '';
  }

  function renderSystem(system) {
    const target = document.getElementById('systemWorkbenchRoot');
    if (!target) return;
    target.innerHTML = `
      <div id="operatorConsole"></div>
      <div class="system-workbench-hero">
        <div class="panel">
          <div class="panel-header"><div><h2>${system.title}</h2><p>${system.desc}</p></div></div>
          <div class="system-action-row">
            <button class="btn primary" onclick="startJob({only_module:'${system.id}',from_module:''})">只运行${system.nav}</button>
            <button class="btn" onclick="switchView('stages')">查看分步输出</button>
            <button class="btn ghost" onclick="switchView('outputs')">查看产物</button>
          </div>
          <div class="system-subnav-note">运行时下方阶段看板会自动高亮当前步骤。${system.kind === 'llm' ? '文本系统会显示模型输出、JSON 解析、评分和修改意见。' : '执行系统会显示任务队列、产物、失败项和重试计划。'}</div>
        </div>
        <div class="panel system-log-panel">
          <div class="panel-header compact"><h2>实时输出</h2></div>
          <pre id="systemMiniLog" class="log-box">等待运行。启动后会同步显示模型输出、JSON 解析、评分、任务执行和重跑日志。</pre>
        </div>
      </div>
      <div class="panel live-stage-panel">
        <div class="live-stage-header">
          <div><h2>制作指挥台</h2><p>跑到“故事理解”就高亮故事理解；跑到“候选资产提取”就高亮候选资产提取。每一步后面直接显示该阶段输出摘要。</p></div>
          <div class="live-stage-legend"><span>蓝色 = 正在运行</span><span>绿色 = 已有输出</span><span>红色 = 失败/需处理</span></div>
        </div>
        <div id="liveStageBoard" class="live-stage-board"></div>
      </div>
      <div class="system-step-grid">
        ${system.stages.map(s => `<div class="system-step-card"><h3>${s[0]}</h3><p>${s[1]}</p><div class="step-meta-list"><span>状态：等待运行</span><span>内容：${system.kind === 'llm' ? '提示词、模型输出、评分、修改意见' : '任务数量、执行状态、产物路径、失败重试'}</span><span>查看：实时输出 + 分步输出</span></div></div>`).join('')}
      </div>
      ${renderExecutionCards(system)}
    `;
    if (window.renderOperatorConsole) window.renderOperatorConsole();
    if (window.renderLiveStageBoard) window.renderLiveStageBoard();
    refreshExecutionCards(system);
  }

  function renderExecutionCards(system) {
    if (!['image', 'audio', 'video', 'assembly'].includes(system.kind)) return '';
    const titleMap = { image: '分镜图任务卡片', audio: '音频任务卡片', video: '视频任务卡片', assembly: '最终合成卡片' };
    return `<div class="panel" style="margin-top:16px"><div class="panel-header"><div><h2>${titleMap[system.kind]}</h2><p>这里不是日志，而是按任务/片段/产物做卡片化展示。</p></div><button class="btn small" onclick="window.refreshCurrentExecutionCards && window.refreshCurrentExecutionCards()">刷新卡片</button></div><div id="executionCardGrid" class="system-step-grid"><div class="muted">等待产物。运行${system.nav}后自动显示。</div></div></div>`;
  }

  async function refreshExecutionCards(system) {
    window.refreshCurrentExecutionCards = () => refreshExecutionCards(system);
    const grid = document.getElementById('executionCardGrid');
    if (!grid) return;
    const runDir = runDirNow();
    if (!runDir) return;
    if (system.kind === 'image') await renderImageCards(grid, runDir);
    if (system.kind === 'audio') await renderAudioCards(grid, runDir);
    if (system.kind === 'video') await renderVideoCards(grid, runDir);
    if (system.kind === 'assembly') await renderAssemblyCards(grid, runDir);
  }

  async function getJson(path) { try { const data = await api(`/api/file?path=${encodeURIComponent(path)}`); return data.type === 'json' ? data.content : null; } catch (_) { return null; } }

  function card(title, desc, rows, actionPath) {
    return `<div class="system-step-card"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(desc || '')}</p><div class="step-meta-list">${rows.map(r => `<span>${escapeHtml(r)}</span>`).join('')}</div>${actionPath ? `<div class="system-action-row"><button class="btn small" onclick="previewFile('${escapeAttr(actionPath)}')">查看文件</button></div>` : ''}</div>`;
  }

  async function renderImageCards(grid, runDir) {
    const data = await getJson(`${runDir}/07_storyboard_image/image_manifest.json`);
    const images = data?.images || data?.image_manifest?.images || [];
    const retry = data?.retry_plan || data?.quality_report?.retry_plan || {};
    if (!images.length) { grid.innerHTML = '<div class="muted">暂无分镜图任务。运行分镜图系统后显示每帧图片卡片。</div>'; return; }
    grid.innerHTML = images.slice(0, 80).map((img, i) => card(`图片任务 ${img.frame_id || i + 1}`, img.execution_mode === 'dry_run' ? 'dry-run 任务，尚未真实生成图片。' : '图片执行任务。', [`图片路径：${img.image_path || '-'}`, `执行状态：${img.status || img.execution_result?.status || '未知'}`, `重试：${retry.needs_retry ? '需要检查失败帧' : '暂无'}`], img.image_path || `${runDir}/07_storyboard_image/image_manifest.json`)).join('');
  }

  async function renderAudioCards(grid, runDir) {
    const manifest = await getJson(`${runDir}/08_audio/audio_manifest.json`);
    const timeline = await getJson(`${runDir}/08_audio/audio_timeline.json`);
    const segments = manifest?.segments || manifest?.audio_segments || timeline?.segments || timeline?.items || [];
    const base = [card('最终音频', '合成后的整章音频。', ['路径：08_audio/final_audio.wav', '字幕：subtitle.srt / subtitle.ass', '时间线：audio_timeline.json'], `${runDir}/08_audio/final_audio.wav`)];
    const segCards = segments.slice(0, 80).map((seg, i) => card(`音频段 ${seg.segment_id || seg.voice_line_id || i + 1}`, seg.text || seg.content || seg.line_text || '配音段。', [`说话人：${seg.speaker || seg.character_name || seg.voice_id || '-'}`, `类型：${seg.line_type || seg.type || '-'}`, `时长：${seg.duration_sec || seg.duration || '-'} 秒`, `状态：${seg.status || '未知'}`], seg.audio_path || `${runDir}/08_audio/audio_timeline.json`));
    grid.innerHTML = [...base, ...segCards].join('');
  }

  async function renderVideoCards(grid, runDir) {
    const data = await getJson(`${runDir}/09_video/video_manifest.json`);
    const segments = data?.video_segments || data?.segments || data?.clips || [];
    if (!segments.length) { grid.innerHTML = '<div class="muted">暂无视频片段。运行视频生成后显示每段视频卡片。</div>'; return; }
    grid.innerHTML = segments.slice(0, 80).map((seg, i) => card(`视频片段 ${seg.segment_id || seg.clip_id || i + 1}`, '按音频时间线和分镜图生成的视频片段。', [`视频路径：${seg.video_path || seg.clip_path || '-'}`, `起止：${seg.start_sec ?? '-'} - ${seg.end_sec ?? '-'} 秒`, `状态：${seg.status || '未知'}`, `重试：${seg.needs_retry ? '需要' : '暂无'}`], seg.video_path || seg.clip_path || `${runDir}/09_video/video_manifest.json`)).join('');
  }

  async function renderAssemblyCards(grid, runDir) {
    const manifest = await getJson(`${runDir}/10_final_assembly/final_manifest.json`);
    const meta = await getJson(`${runDir}/10_final_assembly/final_meta.json`);
    grid.innerHTML = [
      card('输入检查', '检查视频、音频、字幕是否齐全。', [`视频：${manifest?.input_video || meta?.input_video || '等待'}`, `音频：${manifest?.input_audio || meta?.input_audio || '等待'}`, `字幕：${manifest?.subtitle || meta?.subtitle || '等待'}`], `${runDir}/10_final_assembly/final_manifest.json`),
      card('最终成片', '最终导出的完整视频。', ['路径：10_final_assembly/final.mp4', `状态：${manifest?.status || meta?.status || '等待'}`, '导出器：FFmpeg'], `${runDir}/10_final_assembly/final.mp4`),
      card('导出元信息', '最终视频的时长、来源、合成参数。', ['manifest：final_manifest.json', 'meta：final_meta.json'], `${runDir}/10_final_assembly/final_meta.json`)
    ].join('');
  }

  function installNav() {
    const nav = document.querySelector('.nav');
    if (!nav) return;
    nav.innerHTML = '<div class="system-nav-title">分系统</div>' + SYSTEMS.map((s, i) => `<button class="nav-item ${i===1?'active':''}" data-system-id="${s.id}"><span>•</span>${s.nav}</button>`).join('') + '<div class="system-nav-title">辅助</div><button class="nav-item" data-view="runner"><span>▶</span>生产控制台</button><button class="nav-item" data-view="stages"><span>▦</span>分步输出</button><button class="nav-item" data-view="outputs"><span>⌁</span>产物中心</button>';
    nav.querySelectorAll('[data-system-id]').forEach(btn => btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      switchView('system');
      renderSystem(SYSTEMS.find(s => s.id === btn.dataset.systemId) || SYSTEMS[1]);
    }));
    nav.querySelectorAll('[data-view]').forEach(btn => btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      switchView(btn.dataset.view);
    }));
  }

  function installView() {
    const main = document.querySelector('.main');
    if (!main || document.getElementById('view-system')) return;
    const section = document.createElement('section');
    section.className = 'view active';
    section.id = 'view-system';
    section.innerHTML = '<div id="systemWorkbenchRoot"></div>';
    const dashboard = document.getElementById('view-dashboard');
    if (dashboard) dashboard.classList.remove('active');
    main.appendChild(section);
    renderSystem(SYSTEMS[1]);
  }

  const oldConnect = window.connectEvents || connectEvents;
  window.connectEvents = connectEvents = function(jobId) {
    oldConnect(jobId);
    const s = appState();
    const es = s.eventSource;
    if (!es) return;
    es.addEventListener('log', ev => {
      const event = JSON.parse(ev.data);
      const box = document.getElementById('systemMiniLog');
      if (!box) return;
      const line = event.payload.line || '';
      if (line.includes('[LLM_') || line.includes('[JSON_') || line.includes('[STAGE_') || line.includes('[QUALITY]') || line.includes('[07') || line.includes('[08') || line.includes('[09') || line.includes('[10') || /\b(0[1-9]|10)[A-E]\b/.test(line) || line.includes('故事理解') || line.includes('候选资产')) {
        box.textContent = (box.textContent === '等待运行。启动后会同步显示模型输出、JSON 解析、评分、任务执行和重跑日志。' ? '' : box.textContent + '\n') + line;
        box.scrollTop = box.scrollHeight;
      }
    });
    es.addEventListener('snapshot', () => {
      if (window.refreshCurrentExecutionCards) window.refreshCurrentExecutionCards();
      if (window.renderOperatorConsole) window.renderOperatorConsole();
      if (window.renderLiveStageBoard) window.renderLiveStageBoard();
    });
  };

  window.addEventListener('DOMContentLoaded', function () { installView(); installNav(); });
})();