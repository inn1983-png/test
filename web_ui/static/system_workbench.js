(function () {
  const SYSTEMS = [
    { id: '00_main_controller', nav: '总控系统', title: '总控系统', desc: '负责流程校验、运行上下文、数据链路、自检和模块调度。', stages: [
      ['流程校验', '检查 pipeline 顺序和模块契约。'],
      ['运行上下文', '创建项目、书籍、章节的工作区。'],
      ['依赖检查', '检查上游产物是否存在。'],
      ['运行调度', '执行 dry-run、单模块运行或范围运行。']
    ]},
    { id: '01_novel_parser', nav: '小说解析', title: '小说解析系统', desc: '真实 LLM 分阶段解析小说，输出小说理解、段落、事件、候选资产和生产预测。', stages: [
      ['故事理解', '理解世界观、主线、冲突、人物关系。'],
      ['段落拆分', '锁定原文段落边界，避免后续改写原文。'],
      ['事件图谱', '整理事件、冲突、高留存片段。'],
      ['候选资产提取', '提取所有角色、场景、道具候选。'],
      ['生产预测', '预测语音线、视频单元、情绪曲线。'],
      ['总检评分', '综合评分、修改意见、是否触发重跑。']
    ]},
    { id: '02_script_writer', nav: '剧本改编', title: '剧本改编系统', desc: '把小说解析结果改成对白、旁白、心理 OS 和留白结构。', stages: [
      ['剧情拆解', '拆出适合短剧的剧情单元。'],
      ['剧本初稿', '生成对白、旁白、心理 OS 和留白。'],
      ['节奏优化', '优化对白刺激和口播节奏。'],
      ['视觉动作链', '绑定动作、情绪、画面锚点。'],
      ['剧本总检', '检查可配音、可分镜、外观变化。']
    ]},
    { id: '03_character_system', nav: '角色库', title: '角色库系统', desc: '角色合并、角色卡、服装版本、定妆需求。', stages: [['角色归并','合并别名和称谓。'],['角色资产卡','输出角色外观和服装版本。'],['剧本绑定','绑定角色在剧本里的使用。'],['角色总检','检查拆角、漏角、变脸风险。'],['分镜复核','检查分镜是否可直接引用角色。']]},
    { id: '04_scene_system', nav: '场景库', title: '场景库系统', desc: '场景合并、分级、父子场景和参考图计划。', stages: [['场景归并','合并同一地点。'],['场景资产卡','输出场景等级和参考图需求。'],['剧本绑定','绑定使用段落。'],['场景总检','检查主场景和子场景。'],['分镜复核','检查分镜是否可引用。']]},
    { id: '05_prop_system', nav: '道具库', title: '道具库系统', desc: '道具合并、穿戴策略、关键道具参考图计划。', stages: [['道具归并','合并别名道具。'],['道具资产卡','输出道具类型和穿戴策略。'],['剧本绑定','绑定角色、服装和剧情。'],['道具总检','检查漏道具和误分类。'],['分镜复核','检查分镜是否可引用。']]},
    { id: '06_storyboard', nav: '单帧分镜', title: '单帧分镜系统', desc: '资产闸门、单帧分镜、连续性绑定。', stages: [['资产闸门','检查剧本、角色库、场景库、道具库是否齐全。'],['分镜规划','规划帧数和节奏。'],['单帧分镜','输出每帧动作、构图和资产引用。'],['连续性绑定','绑定前后帧衔接。'],['分镜总检','检查资产引用和连续性。']]},
    { id: '07_storyboard_image', nav: '分镜图', title: '分镜图系统', desc: '参考资产准备、图片任务、ComfyUI 或 dry-run 执行。', stages: [['参考资产准备','准备角色、场景、道具参考。'],['图片任务构建','生成每帧图片任务。'],['图片执行','调用 ComfyUI 或 dry-run。'],['图片总检','输出失败帧和重跑计划。']]},
    { id: '08_audio', nav: '音频配音', title: '音频配音系统', desc: '对白、旁白、心理 OS、留白的配音、字幕和时间线。', stages: [['音频队列','构建配音文本队列。'],['音色情绪绑定','绑定说话人、音色和情绪。'],['配音执行','调用 TTS 或 dry-run。'],['混音字幕','输出最终音频、字幕和时间线。']]},
    { id: '09_video', nav: '视频生成', title: '视频生成系统', desc: '按音频和分镜图生成视频片段。', stages: [['输入检查','检查分镜图和音频。'],['视频规划','规划片段和时长。'],['视频执行','调用视频模型或 dry-run。'],['视频总检','输出视频清单和问题。']]},
    { id: '10_final_assembly', nav: '最终合成', title: '最终合成系统', desc: '拼接视频、对齐音频字幕、导出最终成片。', stages: [['输入检查','检查音频和视频片段。'],['视频准备','准备片段列表。'],['音频字幕对齐','对齐音频和字幕。'],['最终导出','导出最终视频。']]}
  ];

  function renderSystem(system) {
    const target = document.getElementById('systemWorkbenchRoot');
    if (!target) return;
    target.innerHTML = `
      <div class="system-workbench-hero">
        <div class="panel">
          <div class="panel-header"><div><h2>${system.title}</h2><p>${system.desc}</p></div></div>
          <div class="system-action-row">
            <button class="btn primary" onclick="startJob({only_module:'${system.id}',from_module:''})">只运行${system.nav}</button>
            <button class="btn" onclick="switchView('stages')">查看分步输出</button>
            <button class="btn ghost" onclick="switchView('outputs')">查看产物</button>
          </div>
          <div class="system-subnav-note">运行时右侧会显示实时输出。分步完成后，可以到“分步输出”里查看评分、问题和 JSON 内容。</div>
        </div>
        <div class="panel system-log-panel">
          <div class="panel-header compact"><h2>实时输出</h2></div>
          <pre id="systemMiniLog" class="log-box">等待运行。启动后会同步显示模型输出、JSON 解析、评分和重跑日志。</pre>
        </div>
      </div>
      <div class="system-step-grid">
        ${system.stages.map(s => `<div class="system-step-card"><h3>${s[0]}</h3><p>${s[1]}</p><div class="step-meta-list"><span>状态：等待运行</span><span>内容：提示词、模型输出、评分、修改意见</span><span>查看：实时输出 + 分步输出</span></div></div>`).join('')}
      </div>`;
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
    const es = state.eventSource;
    if (!es) return;
    es.addEventListener('log', ev => {
      const event = JSON.parse(ev.data);
      const box = document.getElementById('systemMiniLog');
      if (!box) return;
      const line = event.payload.line || '';
      if (line.includes('[LLM_') || line.includes('[JSON_') || line.includes('[STAGE_') || line.includes('[QUALITY]')) {
        box.textContent = (box.textContent === '等待运行。启动后会同步显示模型输出、JSON 解析、评分和重跑日志。' ? '' : box.textContent + '\n') + line;
        box.scrollTop = box.scrollHeight;
      }
    });
  };

  window.addEventListener('DOMContentLoaded', function () {
    installView();
    installNav();
  });
})();