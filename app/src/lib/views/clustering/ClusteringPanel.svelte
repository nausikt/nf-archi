<script lang="ts">
  /**
   * Reduce · Clustering grid view.
   *
   * Composes the generic CosmographCanvas with a control overlay: selectable knob
   * chips (n_components, n_neighbors, algorithm, min_cluster_size, min_samples, k)
   * and a scrollable member list. Selecting a member recolors the fixed umap2 map
   * by that reduce×cluster partition. All data logic lives in ./model.ts.
   */
  import type { Cosmograph } from '@cosmograph/cosmograph';
  import CosmographCanvas from '../../cosmograph/CosmographCanvas.svelte';
  import {
    loadMembers, loadBasePoints, loadRunLabels, buildRunView, buildAxes, filterMembers,
    type Member, type BasePoint, type Axis, type KnobKey, type KnobValue, type RunView,
  } from './model';

  let cosmo = $state<Cosmograph>();
  let members = $state<Member[]>([]);
  let base = $state<BasePoint[]>([]);
  let axes = $state<Axis[]>([]);
  let sel = $state<Partial<Record<KnobKey, KnobValue>>>({});
  let activeRun = $state<string>();
  let runView = $state<RunView>();
  let error = $state<string>();

  const filtered = $derived(filterMembers(members, sel));
  const active = $derived(members.find((m) => m.run === activeRun));
  const status = $derived(
    error ?? (members.length ? `${filtered.length}/${members.length} runs` : 'loading…'),
  );

  const fmt = (v: KnobValue): string => (v === null ? 'none' : String(v));

  // load manifest + base coords once
  $effect(() => {
    let alive = true;
    Promise.all([loadMembers(), loadBasePoints()])
      .then(([ms, bp]) => {
        if (!alive) return;
        members = ms;
        base = bp;
        axes = buildAxes(ms);
        activeRun = ms[0]?.run;
      })
      .catch((e) => { if (alive) error = (e as Error).message; });
    return () => { alive = false; };
  });

  // recolor when the active member changes
  $effect(() => {
    if (!activeRun || base.length === 0) return;
    let alive = true;
    loadRunLabels(activeRun)
      .then((labels) => { if (alive) runView = buildRunView(base, labels); })
      .catch((e) => { if (alive) error = (e as Error).message; });
    return () => { alive = false; };
  });

  function pickKnob(key: KnobKey, value: KnobValue) {
    const next = { ...sel };
    if (next[key] === value) delete next[key];
    else next[key] = value;
    sel = next;
    const hit = filterMembers(members, next);
    if (hit.length && !hit.some((m) => m.run === activeRun)) activeRun = hit[0].run;
  }
  function clearKnobs() { sel = {}; }

  function step(dir: 1 | -1) {
    if (!filtered.length) return;
    const i = filtered.findIndex((m) => m.run === activeRun);
    const n = filtered.length;
    activeRun = filtered[(((i < 0 ? 0 : i) + dir) % n + n) % n].run;
  }
</script>

<CosmographCanvas config={runView?.config} bind:cosmo>
  <aside class="grid-info nodrag nowheel">
    <div class="head">
      <span class="title">GRID</span>
      <span class="status">{status}</span>
    </div>

    {#if active}
      <div class="stats">
        <div><b>{active.n_clusters}</b><span>clusters</span></div>
        <div><b>{active.noise}</b><span>noise</span></div>
        <div><b>{active.silhouette.toFixed(2)}</b><span>silhouette</span></div>
      </div>
      <div class="active-run" title={active.run}>
        <span class="algo">{active.algorithm}</span>
        {#if active.dropped}<span class="dropped">dropped</span>{/if}
        <span class="run">{active.run}</span>
      </div>
    {/if}

    <!-- selectable / scrollable knobs -->
    <div class="knobs">
      <div class="knobs-head">
        <span>HYPERPARAMS</span>
        {#if Object.keys(sel).length}<button class="clear" onclick={clearKnobs}>reset</button>{/if}
      </div>
      {#each axes as axis (axis.key)}
        <div class="axis">
          <span class="axis-title">{axis.title}</span>
          <div class="chips">
            {#each axis.values as v (fmt(v))}
              <button
                class="chip"
                class:on={sel[axis.key] === v}
                class:match={active?.[axis.key] === v}
                onclick={() => pickKnob(axis.key, v)}
              >{fmt(v)}</button>
            {/each}
          </div>
        </div>
      {/each}
    </div>

    <!-- scrollable member list -->
    <div class="runs-head">
      <span>RUNS<span class="muted">{filtered.length}</span></span>
      <span class="stepper">
        <button onclick={() => step(-1)} title="previous">‹</button>
        <button onclick={() => step(1)} title="next">›</button>
      </span>
    </div>
    <div class="runs">
      {#each filtered as m (m.run)}
        <button
          class="run-item"
          class:on={m.run === activeRun}
          class:dim={m.dropped}
          onclick={() => (activeRun = m.run)}
          title={m.run}
        >
          <span class="ri-main">
            <span class="ri-algo">{m.algorithm}</span>
            <span class="ri-knobs">
              n{m.n_components}·nn{m.n_neighbors}{#if m.min_cluster_size}·mcs{m.min_cluster_size}{/if}{#if m.min_samples != null}·ms{m.min_samples}{/if}{#if m.k}·k{m.k}{/if}
            </span>
          </span>
          <span class="ri-metrics">
            <span class="ri-k">{m.n_clusters}c</span>
            <span class="ri-sil">{m.silhouette.toFixed(2)}</span>
          </span>
        </button>
      {/each}
    </div>

    <!-- cluster legend for the active member -->
    {#if runView}
      <div class="legend">
        {#each runView.clusters as c (c.label)}
          <span class="leg"><span class="sw" style:background={c.color}></span>{c.label < 0 ? 'noise' : c.label}<i>{c.count}</i></span>
        {/each}
      </div>
    {/if}
  </aside>
</CosmographCanvas>

<style>
  .grid-info {
    position: absolute;
    top: 12px; left: 12px; bottom: 12px;
    width: 268px;
    display: flex; flex-direction: column;
    padding: 10px;
    overflow: hidden;
    background: rgba(16, 20, 28, .9);
    backdrop-filter: blur(8px);
    border: 1px solid #232936;
    border-radius: 10px;
    box-shadow: 0 8px 28px rgba(0, 0, 0, .45);
    font: 12px/1.4 system-ui, sans-serif;
    color: #e6e9ef;
  }
  .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
  .head .title { font-weight: 700; letter-spacing: .1em; color: #9aa3b2; font-size: 11px; }
  .status { color: #8b929e; font-size: 11px; }

  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 8px; }
  .stats > div { background: #11161f; border: 1px solid #1e2530; border-radius: 8px; padding: 7px 8px; text-align: center; }
  .stats b { display: block; font-size: 16px; color: #e6e9ef; line-height: 1.1; }
  .stats span { color: #8b929e; font-size: 10px; }

  .active-run { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 10px; }
  .active-run .algo { font-weight: 700; color: #7eb6ff; }
  .active-run .dropped { font-size: 9px; text-transform: uppercase; letter-spacing: .06em; color: #ff9b9b; border: 1px solid #5a2e34; border-radius: 4px; padding: 0 4px; }
  .active-run .run { color: #6b7384; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }

  .knobs { margin-bottom: 8px; }
  .knobs-head, .runs-head {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 10px; font-weight: 700; letter-spacing: .08em; color: #7d8696;
    text-transform: uppercase; margin: 2px 0 6px;
  }
  .knobs-head .clear, .stepper button {
    background: #1b2230; color: #cbd2dd; border: 1px solid #2a3140;
    border-radius: 5px; padding: 1px 7px; cursor: pointer; font-size: 10px; line-height: 1.5;
  }
  .knobs-head .clear:hover, .stepper button:hover { background: #232c3c; }
  .stepper { display: flex; gap: 4px; }
  .stepper button { font-size: 13px; padding: 0 7px; }

  .axis { display: grid; grid-template-columns: 92px 1fr; align-items: start; gap: 6px; margin-bottom: 5px; }
  .axis-title { color: #8b929e; font-size: 10.5px; padding-top: 3px; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; }
  .chip {
    background: #11161f; color: #c4ccd8; border: 1px solid #232c3a;
    border-radius: 5px; padding: 2px 7px; cursor: pointer; font-size: 11px;
    font-variant-numeric: tabular-nums;
  }
  .chip:hover { background: #182030; }
  .chip.match { border-color: #355; color: #b6e3da; }
  .chip.on { background: #1d2942; border-color: #3b5680; color: #ffffff; }

  .muted { color: #4f5867; font-weight: 600; margin-left: 5px; }

  .runs { flex: 1 1 0; min-height: 60px; overflow-y: auto; padding-right: 4px; }
  .runs::-webkit-scrollbar { width: 8px; }
  .runs::-webkit-scrollbar-thumb { background: #232936; border-radius: 8px; }

  .run-item {
    display: flex; justify-content: space-between; align-items: center; gap: 6px;
    width: 100%; text-align: left; background: transparent; border: 0;
    border-radius: 5px; padding: 4px 6px; margin: 1px 0; cursor: pointer; color: #c4ccd8;
  }
  .run-item:hover { background: #161d28; }
  .run-item.on { background: #1d2942; color: #fff; }
  .run-item.dim { opacity: .5; }
  .ri-main { display: flex; flex-direction: column; gap: 1px; overflow: hidden; }
  .ri-algo { font-weight: 600; font-size: 11.5px; }
  .ri-knobs { color: #818b9a; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ri-metrics { display: flex; gap: 6px; align-items: center; font-variant-numeric: tabular-nums; }
  .ri-k { color: #8b929e; font-size: 10px; }
  .ri-sil { color: #7ee787; font-size: 11px; }
  .run-item.on .ri-knobs, .run-item.on .ri-k { color: #b9c2d0; }

  .legend {
    display: flex; flex-wrap: wrap; gap: 6px 10px;
    margin-top: 8px; padding-top: 8px; border-top: 1px solid #1e2530;
    max-height: 76px; overflow-y: auto;
  }
  .leg { display: inline-flex; align-items: center; gap: 4px; color: #c4ccd8; font-size: 11px; }
  .leg .sw { width: 9px; height: 9px; border-radius: 2px; }
  .leg i { color: #6b7384; font-style: normal; font-size: 10px; }
</style>
