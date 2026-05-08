import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type NodeItem = Record<string, any> & { id: string; type: string; status: string };
type Snapshot = { project: any; settings: any; canvas: any; nodes: NodeItem[]; tasks: any[]; workflows: any[]; final_manifest?: any };

const API_HOST = 'http://127.0.0.1:7860';
const API = API_HOST + '/api/projects/demo_project';
const pages = [
  { id: 'Dashboard', label: '首页' },
  { id: 'Script', label: '剧本' },
  { id: 'Assets', label: '资产' },
  { id: 'Storyboard', label: '分镜' },
  { id: 'Tasks', label: '任务' },
  { id: 'Preview', label: '成片' },
  { id: 'Settings', label: '设置' },
];
const workflowCategories = ['image', 'video', 'audio', 'grid', 'final', 'utility'];
const stagedActions = [
  ['generate-script', '生成剧本'],
  ['generate-assets', '生成资产'],
  ['generate-storyboard', '生成分镜'],
  ['enqueue-images', '生成图片'],
  ['enqueue-grids', '生成宫格'],
  ['enqueue-audio', '生成音频'],
  ['enqueue-video', '生成视频'],
  ['enqueue-final', '合成成片'],
];

const statusLabels: Record<string, string> = {
  pending: '待处理',
  waiting: '等待',
  waiting_image: '等图片',
  waiting_grid: '等宫格',
  pending_image: '图片队列',
  pending_grid: '宫格队列',
  pending_audio: '音频队列',
  pending_video: '视频队列',
  running: '运行中',
  done: '完成',
  failed: '失败',
  cancelled: '已取消',
  needs_review: '需检查',
  locked: '已锁定',
  missing: '未生成',
  ready: '可执行',
};

function Badge({ value }: { value: string }) { return <span className={'badge ' + value}>{statusLabels[value] || value || '-'}</span>; }

function actionSummary(result: any) {
  if (!result) return '';
  if (result.error) return result.error;
  if (result.message) return result.message;
  if (typeof result.enqueued_count === 'number') return `已加入任务队列：${result.enqueued_count}`;
  if (typeof result.success_count === 'number') return `成功 ${result.success_count}，失败 ${result.failed_count || 0}`;
  if (typeof result.count === 'number') return `已生成：${result.count}`;
  if (typeof result.shots === 'number') return `分镜 ${result.shots}，宫格 ${result.grids || 0}`;
  if (result.action) return `已执行：${result.action}`;
  return '已完成';
}

function ResultNotice({ result }: { result: any }) {
  const summary = actionSummary(result);
  if (!summary) return null;
  return <div className={'notice ' + (result?.error ? 'error' : 'ok')}><b>{result?.error ? '操作失败' : '操作结果'}</b><span>{summary}</span></div>;
}

function App() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [page, setPage] = useState('Dashboard');
  const [selected, setSelected] = useState<NodeItem | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<any>({});
  const [workflowDraft, setWorkflowDraft] = useState({ category: 'image', name: 'workflow.json', content: '' });
  const [sourceDraft, setSourceDraft] = useState({ title: '', content: '' });
  const [taskLog, setTaskLog] = useState('');
  const [actionResult, setActionResult] = useState<any>(null);
  const [checkResult, setCheckResult] = useState<any>(null);
  const [workflowMessage, setWorkflowMessage] = useState('');
  const [voiceLibrary, setVoiceLibrary] = useState<any>(null);
  const [finalManifest, setFinalManifest] = useState<any>(null);

  async function load() {
    const res = await fetch(API);
    const json = await res.json();
    setData(json);
    setSettingsDraft(json.settings || {});
    setFinalManifest(json.final_manifest || null);
  }

  async function post(action: string, body?: any) {
    const res = await fetch(API + '/' + action, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const json = await res.json();
    setActionResult(json);
    await load();
    return json;
  }

  async function importSource() {
    await fetch(API + '/source', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sourceDraft) });
    await load();
  }

  async function patchNode(id: string, patch: any) {
    await fetch(API + '/nodes/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
    await load();
  }

  async function nodeAction(id: string, action: string) {
    const res = await fetch(API + '/nodes/' + id + '/' + action, { method: 'POST' });
    setActionResult(await res.json());
    await load();
  }

  async function batchAction(action: string, nodeIds: string[]) {
    return post('nodes/' + action, { node_ids: nodeIds });
  }

  async function taskAction(id: string, action: string) {
    const res = await fetch(API + '/tasks/' + id + '/' + action, { method: 'POST' });
    const json = await res.json();
    if (action === 'log') setTaskLog(json.log || '');
    else setActionResult(json);
    await load();
  }

  async function saveSettings() {
    await fetch(API + '/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settingsDraft) });
    await load();
  }

  async function uploadWorkflow() {
    try {
      JSON.parse(workflowDraft.content);
    } catch (err: any) {
      setWorkflowMessage('JSON invalid: ' + err.message);
      return;
    }
    const res = await fetch(API + '/workflows', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workflowDraft) });
    const json = await res.json();
    if (!res.ok) setWorkflowMessage(json.error || 'workflow upload failed');
    else {
      setWorkflowMessage('JSON valid / uploaded: ' + json.path);
      setWorkflowDraft({ category: 'image', name: 'workflow.json', content: '' });
    }
    await load();
  }

  async function callCheck(name: string, body?: any) {
    const res = await fetch(API + '/checks/' + name, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const json = await res.json();
    setCheckResult(json);
    if (name === 'indextts-voices') setVoiceLibrary(json);
  }

  async function loadVoiceLibrary() {
    const res = await fetch(API + '/checks/indextts-voices', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    const json = await res.json();
    setVoiceLibrary(json);
  }

  useEffect(() => { load(); loadVoiceLibrary(); }, []);

  const nodes = data?.nodes || [];
  const shots = nodes.filter(n => n.type === 'shot');
  const grids = nodes.filter(n => n.type === 'storyboard_grid');
  const assets = nodes.filter(n => n.type.includes('asset'));
  const scripts = nodes.filter(n => n.type === 'script_block' || n.type === 'source_text' || n.type === 'story_segment');
  const videos = nodes.filter(n => n.type === 'video_clip' || n.video_path);
  const progress = data?.project?.progress || 0;

  const content = useMemo(() => {
    if (!data) return <section className="panel"><h3>Loading...</h3></section>;
    if (page === 'Dashboard') return <Dashboard data={data} shots={shots} grids={grids} assets={assets} sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} post={post} actionResult={actionResult} />;
    if (page === 'Script') return <ScriptPage scripts={scripts} setSelected={setSelected} sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} />;
    if (page === 'Assets') return <AssetPage assets={assets} setSelected={setSelected} patchNode={patchNode} lockAllAssets={() => post('nodes/lock-assets')} actionResult={actionResult} voiceLibrary={voiceLibrary} />;
    if (page === 'Storyboard') return <StoryboardPage shots={shots} grids={grids} setSelected={setSelected} nodeAction={nodeAction} batchAction={batchAction} actionResult={actionResult} />;
    if (page === 'Tasks') return <TaskPage tasks={data.tasks || []} taskAction={taskAction} taskLog={taskLog} />;
    if (page === 'Preview') return <PreviewPage videos={videos} data={data} finalManifest={finalManifest} />;
    return <SettingsPage settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} saveSettings={saveSettings} workflowDraft={workflowDraft} setWorkflowDraft={setWorkflowDraft} uploadWorkflow={uploadWorkflow} workflows={data.workflows || []} callCheck={callCheck} checkResult={checkResult} workflowMessage={workflowMessage} setWorkflowMessage={setWorkflowMessage} voiceLibrary={voiceLibrary} />;
  }, [data, page, selected, settingsDraft, workflowDraft, sourceDraft, taskLog, actionResult, checkResult, workflowMessage, finalManifest, voiceLibrary]);

  return (
    <main className="app">
      <aside className="sidebar">
        <h1>短剧工作台</h1>
        <p className="side-note">demo_project</p>
        <nav>{pages.map(p => <div key={p.id} className={'nav ' + (page === p.id ? 'active' : '')} onClick={() => setPage(p.id)}>{p.label}</div>)}</nav>
        <div className="side-actions">
          <button onClick={() => post('refresh')}>刷新</button>
          <button onClick={() => post('run')}>一键运行</button>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar"><div><h2>{data?.project?.title || 'demo_project'}</h2><p>当前阶段：{data?.project?.current_stage || '-'}</p></div><strong>{progress}%</strong></header>
        {content}
      </section>
      <aside className="drawer">
        <h3>节点详情</h3>
        {selected ? <NodeEditor node={selected} patchNode={patchNode} nodeAction={nodeAction} /> : <p>点击剧本、资产或分镜卡片后，这里会显示详细内容。</p>}
      </aside>
    </main>
  );
}

function SourceImport({ sourceDraft, setSourceDraft, importSource }: any) {
  return <section className="panel source-panel"><div className="section-title"><span className="step-index">1</span><h3>导入小说正文</h3></div><label className="field"><span>项目标题</span><input value={sourceDraft.title} onChange={e => setSourceDraft({ ...sourceDraft, title: e.target.value })} /></label><textarea className="sourcebox" placeholder="把小说正文粘贴到这里" value={sourceDraft.content} onChange={e => setSourceDraft({ ...sourceDraft, content: e.target.value })} /><button className="primary" onClick={importSource}>导入正文</button></section>;
}

function Dashboard({ data, shots, grids, assets, sourceDraft, setSourceDraft, importSource, post, actionResult }: any) {
  const sourceCount = (data.nodes || []).filter((n: any) => n.type === 'source_text').length;
  const scriptCount = (data.nodes || []).filter((n: any) => n.type === 'script_block').length;
  const imageDone = shots.filter((n: any) => n.image_path).length;
  const gridDone = grids.filter((n: any) => n.grid_path).length;
  const audioDone = (data.nodes || []).filter((n: any) => n.audio_path).length;
  const videoDone = grids.filter((n: any) => n.video_path).length;
  const finalDone = data.final_manifest?.status === 'done';
  const tasksRunning = (data.tasks || []).filter((t: any) => ['pending', 'running'].includes(t.status)).length;
  const steps = [
    { key: 'source', title: '导入正文', done: sourceCount > 0, count: sourceCount, action: null },
    { key: 'script', title: '生成剧本', done: scriptCount > 0, count: scriptCount, action: 'generate-script' },
    { key: 'assets', title: '生成资产', done: assets.length > 0, count: assets.length, action: 'generate-assets' },
    { key: 'storyboard', title: '生成分镜', done: shots.length > 0, count: shots.length, action: 'generate-storyboard' },
    { key: 'images', title: '生成图片', done: shots.length > 0 && imageDone === shots.length, count: `${imageDone}/${shots.length}`, action: 'enqueue-images' },
    { key: 'grids', title: '生成宫格', done: grids.length > 0 && gridDone === grids.length, count: `${gridDone}/${grids.length}`, action: 'enqueue-grids' },
    { key: 'audio', title: '生成音频', done: scriptCount > 0 && audioDone === scriptCount, count: `${audioDone}/${scriptCount}`, action: 'enqueue-audio' },
    { key: 'video', title: '生成视频', done: grids.length > 0 && videoDone === grids.length, count: `${videoDone}/${grids.length}`, action: 'enqueue-video' },
    { key: 'final', title: '合成成片', done: finalDone, count: finalDone ? 1 : 0, action: 'enqueue-final' },
  ];
  const next = steps.find(step => !step.done);
  return <><section className="grid4"><Metric title="剧本" value={scriptCount} /><Metric title="资产" value={assets.length} /><Metric title="分镜" value={shots.length} /><Metric title="运行任务" value={tasksRunning} /></section><section className="panel command-panel"><div><h3>推荐下一步</h3><p>{next ? next.title : '全部流程已完成'}</p></div><button className="primary" disabled={!next?.action} onClick={() => next?.action ? post('actions/' + next.action) : null}>{next?.action ? next.title : '等待检查成片'}</button></section><ResultNotice result={actionResult} /><SourceImport sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} /><section className="panel"><div className="section-title"><span className="step-index">2</span><h3>生产流程</h3></div><div className="flow-grid">{steps.map((step, index) => <article className={'flow-card ' + (step.done ? 'complete' : next?.key === step.key ? 'current' : '')} key={step.key}><div><span className="flow-no">{index + 1}</span><h4>{step.title}</h4></div><Badge value={step.done ? 'done' : next?.key === step.key ? 'ready' : 'waiting'} /><strong>{step.count}</strong>{step.action ? <button onClick={() => post('actions/' + step.action)}>{step.title}</button> : null}</article>)}</div></section><section className="panel"><h3>常用操作</h3><div className="actions4"><button onClick={() => post('step')}>执行下一步</button><button onClick={() => post('run')}>一键运行</button><button onClick={() => post('refresh')}>刷新状态</button>{stagedActions.map(([id, label]) => <button key={id} onClick={() => post('actions/' + id)}>{label}</button>)}</div></section><details className="debug-box"><summary>调试信息</summary><pre>{JSON.stringify(data.canvas, null, 2)}</pre></details></>;
}

function Metric({ title, value }: any) { return <div className="metric"><span>{title}</span><strong>{value}</strong></div>; }

function ScriptPage({ scripts, setSelected, sourceDraft, setSourceDraft, importSource }: any) {
  return <><SourceImport sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} /><section className="panel"><h3>剧本文本</h3>{scripts.map((n: any) => <div className="row" key={n.id} onClick={() => setSelected(n)}><span>{n.id}</span><span>{n.title || n.type}</span><Badge value={n.status} /></div>)}</section></>;
}

function AssetPage({ assets, setSelected, patchNode, lockAllAssets, actionResult, voiceLibrary }: any) {
  const [tab, setTab] = useState('角色');
  const typeByTab: any = { 角色: 'character_asset', 场景: 'scene_asset', 道具: 'prop_asset' };
  const visible = assets.filter((asset: any) => asset.type === typeByTab[tab]);
  return <section className="panel"><h3>资产管理</h3><div className="tabs">{Object.keys(typeByTab).map(name => <button key={name} className={tab === name ? 'active' : ''} onClick={() => setTab(name)}>{name}</button>)}</div><button onClick={lockAllAssets}>锁定全部资产</button><ResultNotice result={actionResult} /><div className="cards">{visible.map((n: any) => <AssetCard key={n.id} asset={n} setSelected={setSelected} patchNode={patchNode} voiceLibrary={voiceLibrary} />)}</div></section>;
}

function AssetCard({ asset, setSelected, patchNode, voiceLibrary }: any) {
  const [draft, setDraft] = useState({ visual_lock: asset.visual_lock || '', negative_prompt: asset.negative_prompt || '', locked: Boolean(asset.locked), voice_id: asset.voice_id || '' });
  const voices = voiceLibrary?.voices || [];
  useEffect(() => setDraft({ visual_lock: asset.visual_lock || '', negative_prompt: asset.negative_prompt || '', locked: Boolean(asset.locked), voice_id: asset.voice_id || '' }), [asset.id]);
  const patch = asset.type === 'character_asset' ? draft : { visual_lock: draft.visual_lock, negative_prompt: draft.negative_prompt, locked: draft.locked };
  return <article className="card asset-card" onClick={() => setSelected(asset)}><div className="thumb">资产</div><h4>{asset.name || asset.id}</h4><Badge value={asset.status} /><p>{asset.type}</p>{asset.type === 'character_asset' ? <label className="mini-field"><span>角色音色</span><select value={draft.voice_id} onClick={e => e.stopPropagation()} onChange={e => setDraft({ ...draft, voice_id: e.target.value })}><option value="">未选择</option>{voices.map((v: any) => <option key={v.voice_id} value={v.voice_id}>{v.voice_id} / {v.speaker_name}</option>)}</select></label> : null}<label className="mini-field"><span>视觉锁定</span><textarea value={draft.visual_lock} onClick={e => e.stopPropagation()} onChange={e => setDraft({ ...draft, visual_lock: e.target.value })} /></label><label className="mini-field"><span>反向提示词</span><textarea value={draft.negative_prompt} onClick={e => e.stopPropagation()} onChange={e => setDraft({ ...draft, negative_prompt: e.target.value })} /></label><label className="checkline" onClick={e => e.stopPropagation()}><input type="checkbox" checked={draft.locked} onChange={e => setDraft({ ...draft, locked: e.target.checked })} />锁定</label><button onClick={(e) => { e.stopPropagation(); patchNode(asset.id, patch); }}>保存资产</button></article>;
}

function StoryboardPage({ shots, grids, setSelected, nodeAction, batchAction, actionResult }: any) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const statusOptions = ['all', 'waiting_image', 'pending_image', 'done', 'needs_review', 'failed', 'locked'];
  const needle = query.trim().toLowerCase();
  const filteredShots = shots.filter((shot: any) => {
    const hay = [shot.id, shot.cap, shot.scene, ...(shot.characters || [])].join(' ').toLowerCase();
    const matchesQuery = !needle || hay.includes(needle);
    const matchesStatus = status === 'all' || shot.status === status;
    return matchesQuery && matchesStatus;
  });
  const filteredIds = filteredShots.map((shot: any) => shot.id);
  return <><section className="panel"><h3>分镜列表</h3><div className="filters"><input placeholder="搜索台词、编号、场景或角色" value={query} onChange={e => setQuery(e.target.value)} /><select value={status} onChange={e => setStatus(e.target.value)}>{statusOptions.map(option => <option key={option} value={option}>{option === 'all' ? '全部状态' : statusLabels[option] || option}</option>)}</select></div><div className="actions4"><button onClick={() => batchAction('batch-review', filteredIds)}>批量审核</button><button onClick={() => batchAction('batch-repair', filteredIds)}>批量修复</button><button onClick={() => batchAction('batch-rerun', filteredIds)}>批量重跑</button></div><ResultNotice result={actionResult} /><div className="cards">{filteredShots.map((s: any) => <article className="card" key={s.id} onClick={() => setSelected(s)}><div className="thumb">{s.image_path ? <img src={s.image_path} /> : '分镜'}</div><h4>{s.id}</h4><Badge value={s.status} /><p>{s.cap || 'no cap'}</p><small>{s.scene || ''} {(s.characters || []).join(', ')}</small><button onClick={(e) => { e.stopPropagation(); nodeAction(s.id, 'rerun'); }}>重跑</button></article>)}</div></section><section className="panel"><h3>宫格</h3>{grids.map((g: any) => <div className="row" key={g.id} onClick={() => setSelected(g)}><span>{g.id}</span><span>{g.grid_mode}</span><Badge value={g.status} /></div>)}</section></>;
}

function TaskPage({ tasks, taskAction, taskLog }: any) {
  return <><section className="panel"><h3>任务队列</h3>{tasks.map((t: any) => <div className="task" key={t.task_id}><div><b>{t.task_id}</b><p>{t.executor} / {t.task_type}</p><small>{t.error || t.duration_seconds || ''}</small></div><Badge value={t.status} /><button onClick={() => taskAction(t.task_id, 'retry')}>重试</button><button onClick={() => taskAction(t.task_id, 'cancel')}>取消</button><button onClick={() => taskAction(t.task_id, 'log')}>日志</button></div>)}</section><section className="panel"><h3>任务日志</h3><pre>{taskLog || '点击某个任务的“日志”按钮查看。'}</pre></section></>;
}

function PreviewPage({ videos, data, finalManifest }: any) {
  const manifest = finalManifest || data.final_manifest || {};
  const videoUrl = manifest.video_url ? API_HOST + manifest.video_url : '';
  return <section className="panel"><h3>成片预览</h3><p>输出目录：projects/{data.project.project_id}/final/</p><div className="manifest-grid"><div><b>状态</b><span>{statusLabels[manifest.status] || manifest.status || '-'}</span></div><div><b>输出文件</b><span>{manifest.output || '-'}</span></div><div><b>FFmpeg</b><span>{manifest.ffmpeg_path || '-'}</span></div></div>{manifest.final_file_exists && videoUrl ? <video className="preview-video" controls src={videoUrl} /> : <p>final.mp4 还没有生成。</p>}<details className="debug-box"><summary>final_manifest.json</summary><pre>{JSON.stringify(manifest, null, 2)}</pre></details><h4>视频片段</h4>{videos.map((v: any) => <div className="row" key={v.id}><span>{v.id}</span><span>{v.video_path || '-'}</span><Badge value={v.status} /></div>)}</section>;
}

function MappingField({ settingsDraft, setSettingsDraft, group, keyName, label }: any) {
  const mappings = settingsDraft.workflow_mappings || {};
  const current = mappings[group] || {};
  return <label className="field"><span>{label}</span><input value={current[keyName] || ''} onChange={e => setSettingsDraft({ ...settingsDraft, workflow_mappings: { ...mappings, [group]: { ...current, [keyName]: e.target.value } } })} /></label>;
}

function workflowJsonStatus(content: string) {
  if (!content.trim()) return '等待粘贴 JSON';
  try { JSON.parse(content); return 'JSON valid'; } catch (err: any) { return 'JSON invalid: ' + err.message; }
}

function SettingsPage({ settingsDraft, setSettingsDraft, saveSettings, workflowDraft, setWorkflowDraft, uploadWorkflow, workflows, callCheck, checkResult, workflowMessage, setWorkflowMessage, voiceLibrary }: any) {
  const voiceOptions = voiceLibrary?.voices || [];
  return <><section className="panel"><h3>本地路径</h3>{['comfyui_url','image_workflow','video_workflow','indextts_root','indextts_voice_index','indextts_command','ffmpeg_path'].map(k => <label className="field" key={k}><span>{k}</span><input value={settingsDraft[k] ?? ''} onChange={e => setSettingsDraft({ ...settingsDraft, [k]: e.target.value })} /></label>)}<label className="field"><span>旁白音色</span>{voiceOptions.length ? <select value={settingsDraft.narrator_voice_id || settingsDraft.default_voice_id || ''} onChange={e => setSettingsDraft({ ...settingsDraft, narrator_voice_id: e.target.value, default_voice_id: e.target.value })}>{voiceOptions.map((v: any) => <option key={v.voice_id} value={v.voice_id}>{v.voice_id} / {v.speaker_name}</option>)}</select> : <input value={settingsDraft.narrator_voice_id ?? settingsDraft.default_voice_id ?? ''} onChange={e => setSettingsDraft({ ...settingsDraft, narrator_voice_id: e.target.value, default_voice_id: e.target.value })} />}</label><button onClick={saveSettings}>保存设置</button></section><section className="panel"><h3>设备检测</h3><div className="actions4"><button onClick={() => callCheck('comfyui-ping')}>检测 ComfyUI</button><button onClick={() => callCheck('ffmpeg')}>检测 FFmpeg</button><button onClick={() => callCheck('indextts')}>检测 IndexTTS</button><button onClick={() => callCheck('indextts-voices')}>读取音色库</button><button onClick={() => callCheck('llm')}>检测 LLM</button><button onClick={() => callCheck('workflow-json', { content: workflowDraft.content })}>校验 JSON</button></div>{checkResult ? <pre>{JSON.stringify(checkResult, null, 2)}</pre> : null}</section><section className="panel"><h3>生成参数</h3>{['default_grid_mode','default_video_seconds','task_timeout_seconds','max_retry'].map(k => <label className="field" key={k}><span>{k}</span><input value={settingsDraft[k] ?? ''} onChange={e => setSettingsDraft({ ...settingsDraft, [k]: e.target.value })} /></label>)}<h4>本地 LLM</h4>{['llm_provider','llm_base_url','llm_model','llama_cpp_root','llama_cpp_server_exe','llama_cpp_model_path','llama_cpp_mmproj_path','llama_cpp_context_size','llama_cpp_gpu_layers','llama_cpp_port'].map(k => <label className="field" key={k}><span>{k}</span><input value={settingsDraft[k] ?? ''} onChange={e => setSettingsDraft({ ...settingsDraft, [k]: e.target.value })} /></label>)}<h4>图片 workflow mapping</h4><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="prompt_node" label="prompt_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="prompt_input" label="prompt_input" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="negative_node" label="negative_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="negative_input" label="negative_input" /><h4>视频 workflow mapping</h4><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="prompt_node" label="prompt_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="prompt_input" label="prompt_input" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="image_node" label="image_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="image_input" label="image_input" /><button onClick={saveSettings}>保存设置</button></section><section className="panel"><h3>上传 workflow JSON</h3><label className="field"><span>分类</span><select value={workflowDraft.category} onChange={e => setWorkflowDraft({ ...workflowDraft, category: e.target.value })}>{workflowCategories.map(c => <option key={c} value={c}>{c}</option>)}</select></label><label className="field"><span>文件名</span><input value={workflowDraft.name} onChange={e => setWorkflowDraft({ ...workflowDraft, name: e.target.value })} /></label><textarea placeholder="粘贴 ComfyUI workflow JSON" value={workflowDraft.content} onChange={e => { setWorkflowDraft({ ...workflowDraft, content: e.target.value }); setWorkflowMessage(workflowJsonStatus(e.target.value)); }} /><p>{workflowMessage || workflowJsonStatus(workflowDraft.content)}</p><button onClick={uploadWorkflow}>上传工作流</button><h4>已上传</h4>{workflows.map((w: any) => <div className="row" key={w.path}><span>{w.category}</span><span>{w.name}</span><span>{w.path}</span></div>)}</section></>;
}

function NodeEditor({ node, patchNode, nodeAction }: any) {
  const [draft, setDraft] = useState(JSON.stringify(node, null, 2));
  useEffect(() => setDraft(JSON.stringify(node, null, 2)), [node.id]);
  return <><div className="node-summary"><h4>{node.name || node.title || node.id}</h4><Badge value={node.status} /><p>{node.cap || node.content || node.visual_lock || node.type}</p></div><div className="actions"><button onClick={() => nodeAction(node.id, 'rerun')}>重跑</button><button onClick={() => nodeAction(node.id, 'review')}>审核</button><button onClick={() => nodeAction(node.id, 'repair')}>修复</button><button onClick={() => nodeAction(node.id, 'lock')}>锁定</button></div><details className="debug-box" open={false}><summary>高级 JSON 编辑</summary><textarea className="jsonedit" value={draft} onChange={e => setDraft(e.target.value)} /><button onClick={() => patchNode(node.id, JSON.parse(draft))}>保存 JSON</button></details></>;
}

createRoot(document.getElementById('root')!).render(<App />);
