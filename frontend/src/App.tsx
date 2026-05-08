import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type NodeItem = Record<string, any> & { id: string; type: string; status: string };
type Snapshot = { project: any; settings: any; canvas: any; nodes: NodeItem[]; tasks: any[]; workflows: any[] };

const API = 'http://127.0.0.1:7860/api/projects/demo_project';
const pages = ['Dashboard', 'Script', 'Assets', 'Storyboard', 'Tasks', 'Preview', 'Settings'];
const workflowCategories = ['image', 'video', 'audio', 'grid', 'final', 'utility'];

function Badge({ value }: { value: string }) { return <span className={'badge ' + value}>{value}</span>; }

function App() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [page, setPage] = useState('Dashboard');
  const [selected, setSelected] = useState<NodeItem | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<any>({});
  const [workflowDraft, setWorkflowDraft] = useState({ category: 'image', name: 'workflow.json', content: '' });
  const [sourceDraft, setSourceDraft] = useState({ title: '', content: '' });
  const [taskLog, setTaskLog] = useState('');

  async function load() { const res = await fetch(API); const json = await res.json(); setData(json); setSettingsDraft(json.settings || {}); }
  async function post(action: string) { await fetch(API + '/' + action, { method: 'POST' }); await load(); }
  async function importSource() { await fetch(API + '/source', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sourceDraft) }); await load(); }
  async function patchNode(id: string, patch: any) { await fetch(API + '/nodes/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) }); await load(); }
  async function nodeAction(id: string, action: string) { await fetch(API + '/nodes/' + id + '/' + action, { method: 'POST' }); await load(); }
  async function taskAction(id: string, action: string) { const res = await fetch(API + '/tasks/' + id + '/' + action, { method: 'POST' }); if (action === 'log') { const json = await res.json(); setTaskLog(json.log || ''); } await load(); }
  async function saveSettings() { await fetch(API + '/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settingsDraft) }); await load(); }
  async function uploadWorkflow() { await fetch(API + '/workflows', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(workflowDraft) }); setWorkflowDraft({ category: 'image', name: 'workflow.json', content: '' }); await load(); }

  useEffect(() => { load(); }, []);

  const nodes = data?.nodes || [];
  const shots = nodes.filter(n => n.type === 'shot');
  const grids = nodes.filter(n => n.type === 'storyboard_grid');
  const assets = nodes.filter(n => n.type.includes('asset'));
  const scripts = nodes.filter(n => n.type === 'script_block' || n.type === 'source_text' || n.type === 'story_segment');
  const videos = nodes.filter(n => n.type === 'video_clip' || n.video_path);
  const progress = data?.project?.progress || 0;

  const content = useMemo(() => {
    if (!data) return <section className="panel"><h3>Loading...</h3></section>;
    if (page === 'Dashboard') return <Dashboard data={data} shots={shots} grids={grids} assets={assets} sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} post={post} />;
    if (page === 'Script') return <ScriptPage scripts={scripts} setSelected={setSelected} sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} />;
    if (page === 'Assets') return <AssetPage assets={assets} setSelected={setSelected} />;
    if (page === 'Storyboard') return <StoryboardPage shots={shots} grids={grids} setSelected={setSelected} nodeAction={nodeAction} />;
    if (page === 'Tasks') return <TaskPage tasks={data.tasks || []} taskAction={taskAction} taskLog={taskLog} />;
    if (page === 'Preview') return <PreviewPage videos={videos} data={data} />;
    return <SettingsPage settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} saveSettings={saveSettings} workflowDraft={workflowDraft} setWorkflowDraft={setWorkflowDraft} uploadWorkflow={uploadWorkflow} workflows={data.workflows || []} />;
  }, [data, page, selected, settingsDraft, workflowDraft, sourceDraft, taskLog]);

  return (
    <main className="app">
      <aside className="sidebar">
        <h1>Agent Canvas</h1>
        <button onClick={() => post('init')}>初始化项目</button>
        <button onClick={() => post('step')}>执行一步</button>
        <button onClick={() => post('run')}>运行到空闲</button>
        <nav>{pages.map(p => <div key={p} className={'nav ' + (page === p ? 'active' : '')} onClick={() => setPage(p)}>{p}</div>)}</nav>
      </aside>
      <section className="workspace">
        <header className="topbar"><div><h2>{data?.project?.title || 'demo_project'}</h2><p>stage: {data?.project?.current_stage || '-'}</p></div><strong>{progress}%</strong></header>
        {content}
      </section>
      <aside className="drawer">
        <h3>Node Detail</h3>
        {selected ? <NodeEditor node={selected} patchNode={patchNode} nodeAction={nodeAction} /> : <p>选择一个节点查看详情。</p>}
      </aside>
    </main>
  );
}

function SourceImport({ sourceDraft, setSourceDraft, importSource }: any) { return <section className="panel"><h3>导入小说原文</h3><label className="field"><span>标题</span><input value={sourceDraft.title} onChange={e => setSourceDraft({ ...sourceDraft, title: e.target.value })} /></label><textarea className="sourcebox" placeholder="粘贴小说正文" value={sourceDraft.content} onChange={e => setSourceDraft({ ...sourceDraft, content: e.target.value })} /><button onClick={importSource}>导入原文并清空旧生成内容</button></section>; }
function Dashboard({ data, shots, grids, assets, sourceDraft, setSourceDraft, importSource, post }: any) { return <><section className="grid4"><Metric title="Shots" value={shots.length} /><Metric title="Grids" value={grids.length} /><Metric title="Assets" value={assets.length} /><Metric title="Tasks" value={(data.tasks || []).length} /></section><section className="panel"><h3>生产操作</h3><div className="actions4"><button onClick={() => post('step')}>下一步</button><button onClick={() => post('run')}>一键运行</button><button onClick={() => post('refresh')}>刷新 Canvas</button></div></section><SourceImport sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} /><section className="panel"><h3>Canvas Snapshot</h3><pre>{JSON.stringify(data.canvas, null, 2)}</pre></section></>; }
function Metric({ title, value }: any) { return <div className="metric"><span>{title}</span><strong>{value}</strong></div>; }
function ScriptPage({ scripts, setSelected, sourceDraft, setSourceDraft, importSource }: any) { return <><SourceImport sourceDraft={sourceDraft} setSourceDraft={setSourceDraft} importSource={importSource} /><section className="panel"><h3>Script Editor</h3>{scripts.map((n: any) => <div className="row" key={n.id} onClick={() => setSelected(n)}><span>{n.id}</span><span>{n.title || n.type}</span><Badge value={n.status} /></div>)}</section></>; }
function AssetPage({ assets, setSelected }: any) { return <section className="panel"><h3>Asset Hub</h3><div className="cards">{assets.map((n: any) => <article className="card" key={n.id} onClick={() => setSelected(n)}><div className="thumb">ASSET</div><h4>{n.name || n.id}</h4><Badge value={n.status} /><p>{n.visual_lock || ''}</p></article>)}</div></section>; }
function StoryboardPage({ shots, grids, setSelected, nodeAction }: any) { return <><section className="panel"><h3>Timeline / Board</h3><div className="cards">{shots.map((s: any) => <article className="card" key={s.id} onClick={() => setSelected(s)}><div className="thumb">{s.image_path ? <img src={s.image_path} /> : 'SHOT'}</div><h4>{s.id}</h4><Badge value={s.status} /><p>{s.cap || 'no cap'}</p><button onClick={(e) => { e.stopPropagation(); nodeAction(s.id, 'rerun'); }}>重跑</button></article>)}</div></section><section className="panel"><h3>Grid View</h3>{grids.map((g: any) => <div className="row" key={g.id} onClick={() => setSelected(g)}><span>{g.id}</span><span>{g.grid_mode}</span><Badge value={g.status} /></div>)}</section></>; }
function TaskPage({ tasks, taskAction, taskLog }: any) { return <><section className="panel"><h3>Task Center</h3>{tasks.map((t: any) => <div className="task" key={t.task_id}><div><b>{t.task_id}</b><p>{t.executor} / {t.task_type}</p><small>{t.error || t.duration_seconds || ''}</small></div><Badge value={t.status} /><button onClick={() => taskAction(t.task_id, 'retry')}>重试</button><button onClick={() => taskAction(t.task_id, 'cancel')}>取消</button><button onClick={() => taskAction(t.task_id, 'log')}>日志</button></div>)}</section><section className="panel"><h3>Task Log</h3><pre>{taskLog || '点击任务日志查看。'}</pre></section></>; }
function PreviewPage({ videos, data }: any) { return <section className="panel"><h3>Preview</h3><p>最终输出目录：projects/{data.project.project_id}/final/</p>{videos.map((v: any) => <div className="row" key={v.id}><span>{v.id}</span><span>{v.video_path || '-'}</span><Badge value={v.status} /></div>)}</section>; }
function MappingField({ settingsDraft, setSettingsDraft, group, keyName, label }: any) { const mappings = settingsDraft.workflow_mappings || {}; const current = mappings[group] || {}; return <label className="field"><span>{label}</span><input value={current[keyName] || ''} onChange={e => setSettingsDraft({ ...settingsDraft, workflow_mappings: { ...mappings, [group]: { ...current, [keyName]: e.target.value } } })} /></label>; }
function SettingsPage({ settingsDraft, setSettingsDraft, saveSettings, workflowDraft, setWorkflowDraft, uploadWorkflow, workflows }: any) { return <><section className="panel"><h3>Settings</h3>{['comfyui_url','image_workflow','video_workflow','indextts_command','default_voice_id','ffmpeg_path','default_grid_mode','default_video_seconds','task_timeout_seconds','max_retry'].map(k => <label className="field" key={k}><span>{k}</span><input value={settingsDraft[k] ?? ''} onChange={e => setSettingsDraft({ ...settingsDraft, [k]: e.target.value })} /></label>)}<h4>Image Workflow Mapping</h4><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="prompt_node" label="prompt_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="prompt_input" label="prompt_input" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="negative_node" label="negative_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="image" keyName="negative_input" label="negative_input" /><h4>Video Workflow Mapping</h4><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="prompt_node" label="prompt_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="prompt_input" label="prompt_input" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="image_node" label="image_node" /><MappingField settingsDraft={settingsDraft} setSettingsDraft={setSettingsDraft} group="video" keyName="image_input" label="image_input" /><button onClick={saveSettings}>保存设置</button></section><section className="panel"><h3>ComfyUI 工作流 JSON 在线上传</h3><label className="field"><span>分类</span><select value={workflowDraft.category} onChange={e => setWorkflowDraft({ ...workflowDraft, category: e.target.value })}>{workflowCategories.map(c => <option key={c} value={c}>{c}</option>)}</select></label><label className="field"><span>文件名</span><input value={workflowDraft.name} onChange={e => setWorkflowDraft({ ...workflowDraft, name: e.target.value })} /></label><textarea placeholder="粘贴 ComfyUI workflow JSON，或 base64 JSON" value={workflowDraft.content} onChange={e => setWorkflowDraft({ ...workflowDraft, content: e.target.value })} /><button onClick={uploadWorkflow}>上传工作流</button><h4>已上传</h4>{workflows.map((w: any) => <div className="row" key={w.path}><span>{w.category}</span><span>{w.name}</span><span>{w.path}</span></div>)}</section></>; }
function NodeEditor({ node, patchNode, nodeAction }: any) { const [draft, setDraft] = useState(JSON.stringify(node, null, 2)); useEffect(() => setDraft(JSON.stringify(node, null, 2)), [node.id]); return <><div className="actions"><button onClick={() => nodeAction(node.id, 'rerun')}>重跑</button><button onClick={() => nodeAction(node.id, 'review')}>审核</button><button onClick={() => nodeAction(node.id, 'repair')}>修复</button><button onClick={() => nodeAction(node.id, 'lock')}>锁定</button></div><textarea className="jsonedit" value={draft} onChange={e => setDraft(e.target.value)} /><button onClick={() => patchNode(node.id, JSON.parse(draft))}>保存节点</button></>; }

createRoot(document.getElementById('root')!).render(<App />);
