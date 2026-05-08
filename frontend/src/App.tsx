import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type NodeItem = {
  id: string;
  type: string;
  status: string;
  cap?: string;
  image_prompt?: string;
  negative_prompt?: string;
  grid_mode?: string;
  shot_ids?: string[];
};

type Snapshot = {
  project: any;
  canvas: any;
  nodes: NodeItem[];
  tasks: any[];
};

const API = 'http://127.0.0.1:7860/api/projects/demo_project';

function Badge({ value }: { value: string }) {
  return <span className={'badge ' + value}>{value}</span>;
}

function App() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [selected, setSelected] = useState<NodeItem | null>(null);

  async function load() {
    const res = await fetch(API);
    setData(await res.json());
  }

  async function post(action: string) {
    await fetch(API + '/' + action, { method: 'POST' });
    await load();
  }

  useEffect(() => { load(); }, []);

  const nodes = data?.nodes || [];
  const shots = nodes.filter(n => n.type === 'shot');
  const grids = nodes.filter(n => n.type === 'storyboard_grid');
  const assets = nodes.filter(n => n.type.includes('asset'));

  return (
    <main className="app">
      <aside className="sidebar">
        <h1>Agent Canvas</h1>
        <button onClick={() => post('init')}>Init Project</button>
        <button onClick={() => post('step')}>Run Step</button>
        <button onClick={() => post('run')}>Run All</button>
        <section>
          <h3>Stages</h3>
          {['style','source','script','assets','storyboard','images','audio','video','final'].map(s => (
            <div className="stage" key={s}>{s}</div>
          ))}
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h2>{data?.project?.title || 'demo_project'}</h2>
            <p>stage: {data?.project?.current_stage || '-'}</p>
          </div>
          <strong>{data?.project?.progress || 0}%</strong>
        </header>

        <section className="panel">
          <h3>Storyboard Canvas</h3>
          <div className="cards">
            {shots.map(shot => (
              <article className="card" key={shot.id} onClick={() => setSelected(shot)}>
                <div className="thumb">SHOT</div>
                <h4>{shot.id}</h4>
                <Badge value={shot.status} />
                <p>{shot.cap || 'no cap'}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="grid2">
          <div className="panel">
            <h3>Grid View</h3>
            {grids.map(grid => (
              <div className="row" key={grid.id} onClick={() => setSelected(grid)}>
                <span>{grid.id}</span>
                <span>{grid.grid_mode}</span>
                <Badge value={grid.status} />
              </div>
            ))}
          </div>
          <div className="panel">
            <h3>Asset Hub</h3>
            {assets.map(asset => (
              <div className="row" key={asset.id} onClick={() => setSelected(asset)}>
                <span>{asset.id}</span>
                <Badge value={asset.status} />
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h3>Task Center</h3>
          {(data?.tasks || []).map(task => (
            <div className="row" key={task.task_id}>
              <span>{task.task_id}</span>
              <span>{task.executor}</span>
              <Badge value={task.status} />
            </div>
          ))}
        </section>
      </section>

      <aside className="drawer">
        <h3>Node Detail</h3>
        {selected ? <pre>{JSON.stringify(selected, null, 2)}</pre> : <p>Select a node.</p>}
      </aside>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
