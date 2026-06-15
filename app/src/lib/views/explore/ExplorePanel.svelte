<script lang="ts">
  /**
   * Explore embedding view (UMAP2) — frozen.
   *
   * Composes the generic CosmographCanvas with this context's overlay: the INFO
   * panel (clustering summary + many-to-many tag/flag/category distributions),
   * the native search, and the clickable tag legend. All explore-specific data
   * lives in ./model.ts; this file owns only presentation + interaction wiring.
   */
  import { CosmographSearch, CosmographTypeColorLegend, type Cosmograph } from '@cosmograph/cosmograph';
  import CosmographCanvas from '../../cosmograph/CosmographCanvas.svelte';
  import {
    buildExploreModel, summarize, distSingle, distMulti,
    type ExploreModel, type Bin,
  } from './model';

  let cosmo = $state<Cosmograph>();
  let model = $state<ExploreModel>();
  let error = $state<string>();
  let active = $state<string | undefined>(undefined); // "kind:value" highlighted

  let searchEl: HTMLDivElement;
  let legendEl: HTMLDivElement;

  const pts = $derived(model?.pts ?? []);
  const tagColor = $derived(model?.tagColor ?? new Map<string, string>());
  const summary = $derived(summarize(pts));
  const dists = $derived({
    Categories: distSingle(pts, 'top_category'),
    Tags: distMulti(pts, 'tags', tagColor),
    Flags: distMulti(pts, 'flags'),
  });
  const status = $derived(error ?? (model ? `${pts.length} points` : 'loading…'));

  function pick(kind: string, bin: Bin) {
    if (!cosmo) return;
    const key = `${kind}:${bin.value}`;
    if (active === key) { cosmo.unselectAllPoints(); active = undefined; }
    else { cosmo.selectPoints(bin.indices); active = key; }
  }
  function clearSel() { cosmo?.unselectAllPoints(); active = undefined; }

  // load the context model once
  $effect(() => {
    let alive = true;
    buildExploreModel()
      .then((m) => { if (alive) model = m; })
      .catch((e) => { if (alive) error = (e as Error).message; });
    return () => { alive = false; };
  });

  // mount native overlay components once the instance + model are ready
  $effect(() => {
    if (!cosmo || !model) return;
    const search = new CosmographSearch(cosmo, searchEl, {
      placeholderText: 'Search…',
      showAccessorsMenu: true,
      showFooter: true,
      accessor: 'tags_all',
      suggestionFields: { tags_all: 'Tags', flags_all: 'Flags', top_category: 'Category', sample_id: 'ID' },
    });
    let legend: CosmographTypeColorLegend | undefined;
    if (model.hasTag) {
      legend = new CosmographTypeColorLegend(cosmo, legendEl, {
        selectOnClick: true, showLabel: true, labelResolver: () => 'Tags',
      });
    }
    return () => {
      try { search.remove(); } catch { /* noop */ }
      try { legend?.remove(); } catch { /* noop */ }
    };
  });
</script>

<CosmographCanvas config={model?.config} bind:cosmo>
  <!-- LEFT: info / search / distributions -->
  <aside class="info nodrag nowheel">
    <div class="head">
      <span class="title">INFO</span>
      <span class="status">{status}</span>
    </div>

    <div class="stats">
      <div><b>{summary.clusters}</b><span>clusters</span></div>
      <div><b>{summary.points}</b><span>points</span></div>
      <div><b>{summary.noise}</b><span>noise</span></div>
    </div>

    <div class="search-host" bind:this={searchEl}></div>

    {#if active}
      <button class="clear" onclick={clearSel}>clear selection</button>
    {/if}

    <div class="sections">
      {#each Object.entries(dists) as [kind, bins] (kind)}
        <section>
          <h4>{kind}<span class="muted">{bins.length}</span></h4>
          {#each bins as bin (bin.value)}
            {@const max = bins[0]?.count || 1}
            <button
              class="bin"
              class:on={active === `${kind}:${bin.value}`}
              onclick={() => pick(kind, bin)}
              title={bin.value}
            >
              <span class="bar" style:width={`${(bin.count / max) * 100}%`}></span>
              {#if bin.color}<span class="dot" style:background={bin.color}></span>{/if}
              <span class="label">{bin.value}</span>
              <span class="count">{bin.count}</span>
            </button>
          {/each}
        </section>
      {/each}
    </div>
  </aside>

  <!-- BOTTOM-LEFT (on canvas): clickable tag legend -->
  <div class="legend nodrag nowheel" bind:this={legendEl}></div>
</CosmographCanvas>

<style>
  .info, .legend {
    position: absolute;
    background: rgba(16, 20, 28, .9);
    backdrop-filter: blur(8px);
    border: 1px solid #232936;
    border-radius: 10px;
    box-shadow: 0 8px 28px rgba(0, 0, 0, .45);
    font: 12px/1.4 system-ui, sans-serif;
    color: #e6e9ef;
  }

  .info {
    top: 12px; left: 12px; bottom: 12px;
    width: 232px;
    display: flex; flex-direction: column;
    padding: 10px;
    overflow: hidden;
  }
  .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
  .head .title { font-weight: 700; letter-spacing: .1em; color: #9aa3b2; font-size: 11px; }
  .status { color: #8b929e; font-size: 11px; }

  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 10px; }
  .stats > div { background: #11161f; border: 1px solid #1e2530; border-radius: 8px; padding: 7px 8px; text-align: center; }
  .stats b { display: block; font-size: 17px; color: #e6e9ef; line-height: 1.1; }
  .stats span { color: #8b929e; font-size: 10px; }

  .search-host { margin-bottom: 8px; overflow: hidden; }

  .clear {
    align-self: flex-start;
    background: #1b2230; color: #cbd2dd; border: 1px solid #2a3140;
    border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 11px; margin-bottom: 8px;
  }
  .clear:hover { background: #232c3c; }

  .sections { flex: 1 1 0; min-height: 0; overflow-y: auto; padding-right: 4px; }
  .sections::-webkit-scrollbar { width: 8px; }
  .sections::-webkit-scrollbar-thumb { background: #232936; border-radius: 8px; }
  section { margin-bottom: 14px; }
  h4 {
    display: flex; justify-content: space-between; align-items: center;
    margin: 0 0 6px; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; color: #7d8696;
  }
  h4 .muted { color: #4f5867; font-weight: 600; }

  .bin {
    position: relative;
    display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 6px;
    width: 100%; text-align: left;
    background: transparent; border: 0; border-radius: 5px;
    padding: 3px 6px; margin: 1px 0; cursor: pointer; color: #c4ccd8;
    overflow: hidden; font-size: 11.5px;
  }
  .bin:hover { background: #161d28; }
  .bin.on { background: #1d2942; color: #ffffff; }
  .bin .bar {
    position: absolute; inset: 0 auto 0 0; z-index: 0;
    background: linear-gradient(90deg, rgba(126,182,255,.28), rgba(126,182,255,.05));
    border-radius: 5px;
  }
  .bin .dot { position: relative; z-index: 1; width: 8px; height: 8px; border-radius: 50%; }
  .bin .label { position: relative; z-index: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bin .count { position: relative; z-index: 1; color: #818b9a; font-variant-numeric: tabular-nums; }
  .bin.on .count { color: #cbd2dd; }

  .legend { left: 256px; bottom: 12px; max-width: 360px; padding: 8px 10px; }
</style>
