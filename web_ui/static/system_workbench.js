(function () {
  const SYSTEMS = [
    { id: '00_main_controller', title: '00 总控系统', desc: 'pipeline 校验、上下文、数据链路、自检、范围调度。', stages: [
      ['00A', 'pipeline 校验', '检查 pipeline.json 顺序和模块契约。'],
      ['00B', '运行上下文', '创建 project/book/chapter workspace。'],
      ['00C', '依赖检查', '检查上游产物是否存在。'],
      ['00D', 'dry-run / 调度', '只打印计划或执行模块。']
    ]},
    { id: '01_novel_parser', title: '01 小说解析系统', desc: '真实 LLM 分阶段解析小说，输出 novel_analysis.json。', stages: [
      ['01A', '故事理解', '理解世界观、主线、冲突、人物关系。'],
      ['01B', '段落拆分', '锁定 paragraph_id 和原文边界。'],
      ['01C', '事件图谱', '生成事件、冲突、高留存段落。'],
      ['01D', '候选资产提取', '提取所有角色、场景、道具候选。'],
      ['01E', '生产预测', '预测语音线、视频单元、情绪曲线。'],
      ['01F', '总检评分', '综合评分、修改意见、是否触发重跑。']
    ]},
    { id: '02_script_writer', title: '02 剧本改编系统', desc: '把小说解析结果改成对白 + OS + 留白的短剧剧本。', stages: [
      ['02A', '剧情拆解', '拆出可改编剧情单元。'],
      ['02B', '剧本初稿', '生成对白、OS、留白。'],
      ['02C', '节奏优化', '优化对白刺激和口播节奏。'],
      ['02D', '视觉动作链', '绑定动作、情绪、画面锚点。'],
      ['02E', '剧本总检', '检查可配音、可分镜、外观变化。']
    ]},
    { id: '03_character_system', title: '03 角色库系统', desc: '角色合并、角色卡、服装版本、定妆需求。', stages: [['03A','角色归并','合并别名/称谓。'],['03B','角色资产卡','输出角色外观和服装版本。'],['03C','剧本绑定','绑定剧本使用。'],['03D','角色总检','检查拆角/漏角。'],['03E','面向分镜复核','检查 06 可直接引用。']]},
    { id: '04_scene_system', title: '04 场景库系统', desc: '场景合并、分级、父子场景和参考图计划。', stages: [['04A','场景归并','合并同一地点。'],['04B','场景资产卡','输出场景等级和参考图需求。'],['04C','剧本绑定','绑定使用段落。'],['04D','场景总检','检查主场景/子场景。'],['04E','面向分镜复核','检查 06 可引用。']]},
    { id: '05_prop_system', title: '05 道具库系统', desc: '道具合并、穿戴策略、关键道具参考图计划。', stages: [['05A','道具归并','合并别名道具。'],['05B','道具资产卡','输出 prop_type 和 wearable_policy。'],['05C','剧本绑定','绑定角色/服装/剧情。'],['05D','道具总检','检查漏道具和误分类。'],['05E','面向分镜复核','检查 06 可引用。']]},
    { id: '06_storyboard', title: '06 单帧分镜系统', desc: '资产闸门、单帧分镜、连续性绑定。', stages: [['06A','资产闸门','检查 02/03/04/05 是否齐全。'],['06B','分镜规划','规划帧数和节奏。'],['06C','单帧分镜','输出每帧动作/构图/引用。'],['06D','连续性绑定','绑定前后帧衔接。'],['06E','分镜总检','检查资产引用和连续性。']]},
    { id: '07_storyboard_image', title: '07 分镜图系统', desc: '参考资产准备、图片任务、ComfyUI/dry_run 执行。', stages: [['07A','参考资产准备','准备角色/场景/道具参考。'],['07B','图片任务构建','生成 frame image tasks。'],['07C','图片执行','调用 ComfyUI 或 dry_run。'],['07D','图片总检','输出 retry_frames。']]},
    { id: '08_audio', title: '08 音频系统', desc: 'N/D/M/S 配音、音色绑定、字幕和时间线。', stages: [['08A','音频队列','构建 voice lines。'],['08B','音色情绪绑定','绑定 speaker 和 emotion。'],['08C','TTS 执行','IndexTTS2 或 dry_run。'],['08D','混音字幕','输出 final_audio 和字幕。']]},
    { id: '09_video', title: '09 视频系统', desc: '按音频和分镜图生成视频片段。', stages: [['09A','输入检查','检查 07/08。'],['09B','视频规划','规划片段。'],['09C','视频执行','调用视频模型或 dry_run。'],['09D','视频总检','输出 manifest。']]},
    { id: '10_final_assembly', title: '10 最终合成系统', desc: '拼接视频、对齐音频字幕、导出最终成片。', stages: [['10A','输入检查','检查 08/09。'],['10B','视频准备','准备 clips。'],['10C','音频字幕对齐','对齐 audio/subtitle。'],['10D','最终导出','FFmpeg 输出 final.mp4。']]}
  ];

  function renderSystem(system) {
    const target = document.getElementById('systemWorkbenchRoot');
    if (!target) return;
    target.innerHTML = `
      <div class="system-workbench-hero">
        <div class="panel">
          <div class="panel-header"><div><h2>${system.title}</h2><p>${system.desc}</p></div></div>
          <div class="system-action-row">
            <button class="btn primary" onclick="startJob({only_module:'${system.id}',from_module:''})">只运行 ${system.title}</button>
            <button class="btn" onclick="switchView('stages')">查看阶段输出 JSON</button>
            <button class="btn ghost" onclick="switchView('outputs')">查看产物中心</button>
          </div>
          <div class="system-subnav-note">运行时右侧实时日志会显示当前 LLM 输出；阶段完成后，下面卡片可在阶段透明区看到评分和 JSON。</div>
        </div>
        <div class="panel system-log-panel">
          <div class="panel-header compact"><h2>实时输出</h2></div>
          <pre id="systemMiniLog" class="log-box">等待运行。启动后会同步显示 LLM_STREAM / JSON_PARSE / 阶段评分日志。</pre>
        </div>
      </div>
      <div class="system-step-grid">
        ${system.stages.map(s => `<div class="system-step-card"><h3>${s[0]} · ${s[1]}</h3><p>${s[2]}</p><div class="step-meta-list"><span>状态：等待运行</span><span>输出：intermediate/${s[0]}*.json</span><span>显示：实时日志 + 阶段透明区</span></div></div>`).join('')}
      </div>`;
  }

  function installNav() {
    const nav = document.querySelector('.nav');
    if (!nav) return;
    nav.innerHTML = '<div class="system-nav-title">分系统</div>' + SYSTEMS.map((s, i) => `<button class="nav-item ${i===1?'active':''}" data-system-id="${s.id}"><span>${s.id.slice(0,2)}</span>${s.title}</button>`).join('') + '<div class="system-nav-title">总览</div><button class="nav-item" data-view="runner"><span>▶</span>生产控制台</button><button class="nav-item" data-view="stages"><span>▦</span>阶段透明区</button><button class="nav-item" data-view="outputs"><span>⌁</span>产物中心</button>';
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
    const es = state.eventSource;
    if (!es) return;
    es.addEventListener('log', ev => {
      const event = JSON.parse(ev.data);
      const box = document.getElementById('systemMiniLog');
      if (!box) return;
      const line = event.payload.line || '';
      if (line.includes('[LLM_') || line.includes('[JSON_') || line.includes('[STAGE_') || line.includes('[QUALITY]')) {
        box.textContent = (box.textContent === '等待运行。启动后会同步显示 LLM_STREAM / JSON_PARSE / 阶段评分日志。' ? '' : box.textContent + '\n') + line;
        box.scrollTop = box.scrollHeight;
      }
    });
  };

  window.addEventListener('DOMContentLoaded', function () {
    installView();
    installNav();
  });
})();