<script lang="ts">
  /**
   * Sampled view — representatives over the embedding space.
   *
   * Small overlay: the per-role sample counts (medoid / boundary / outlier) and
   * a legend that shows BOTH the colour and the shape of every marker kind. All
   * data logic lives in ./model.ts; this file owns presentation only.
   */
  import type { Cosmograph } from '@cosmograph/cosmograph';
  import CosmographCanvas from '../../cosmograph/CosmographCanvas.svelte';
  import { buildSampledModel, ROLE_STYLES, ANCHOR_STYLES, type SampledModel, type ShapeName } from './model';

  let cosmo = $state<Cosmograph>();
  let model = $state<SampledModel>();
  let error = $state<string>();

  const status = $derived(error ?? (model ? 'ready' : 'loading…'));

  $effect(() => {
    let alive = true;
    buildSampledModel()
      .then((m) => { if (alive) model = m; })
      .catch((e) => { if (alive) error = (e as Error).message; });
    return () => { alive = false; };
  });
</script>

{#snippet glyph(shape: ShapeName, color: string)}
  <svg class="gl" viewBox="0 0 16 16" aria-hidden="true">
    {#if shape === 'circle'}
      <circle cx="8" cy="8" r="5" fill={color} />
    {:else if shape === 'square'}
      <rect x="3" y="3" width="10" height="10" rx="1.5" fill={color} />
    {:else if shape === 'triangle'}
      <polygon points="8,2 14.5,14 1.5,14" fill={color} />
    {:else if shape === 'diamond'}
      <polygon points="8,1.5 14.5,8 8,14.5 1.5,8" fill={color} />
    {:else if shape === 'star'}
      <polygon points="8,1.5 9.8,6.1 14.6,6.3 10.8,9.3 12.1,14 8,11.2 3.9,14 5.2,9.3 1.4,6.3 6.2,6.1" fill={color} />
    {:else if shape === 'cross'}
      <path d="M8 2.5 V13.5 M2.5 8 H13.5" stroke={color} stroke-width="2.4" stroke-linecap="round" />
    {/if}
  </svg>
{/snippet}

<CosmographCanvas config={model?.config} bind:cosmo>
  <aside class="sampled-info nodrag nowheel">
    <div class="head">
      <span class="title">SAMPLED</span>
      <span class="status">{status}</span>
    </div>

    {#if model}
      <div class="stats">
        {#each ROLE_STYLES as s (s.role)}
          <div>
            <b style:color={s.color}>{model.roleCounts[s.role]}</b>
            <span>{s.label.toLowerCase()}</span>
          </div>
        {/each}
      </div>

      <div class="legend">
        <h4>Representatives</h4>
        {#each ROLE_STYLES as s (s.role)}
          <span class="leg">
            {@render glyph(s.shape, s.color)}
            <span class="lbl">{s.label}</span>
            <i>{model.roleCounts[s.role]}</i>
          </span>
        {/each}

        <h4>Anchors</h4>
        {#each ANCHOR_STYLES as s (s.kind)}
          <span class="leg">
            {@render glyph(s.shape, s.color)}
            <span class="lbl">{s.label}</span>
            <i>{model.anchorCounts[s.kind]}</i>
          </span>
        {/each}

        <span class="leg muted">
          {@render glyph('circle', '#39414f')}
          <span class="lbl">Sample</span>
        </span>
      </div>
    {/if}
  </aside>
</CosmographCanvas>

<style>
  .sampled-info {
    position: absolute;
    top: 12px; left: 12px;
    width: 188px;
    display: flex; flex-direction: column;
    padding: 10px;
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

  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 12px; }
  .stats > div { background: #11161f; border: 1px solid #1e2530; border-radius: 8px; padding: 7px 4px; text-align: center; }
  .stats b { display: block; font-size: 17px; line-height: 1.1; }
  .stats span { color: #8b929e; font-size: 9.5px; }

  .legend { display: flex; flex-direction: column; gap: 3px; }
  h4 {
    margin: 6px 0 3px; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; color: #7d8696;
  }
  .leg { display: grid; grid-template-columns: 18px 1fr auto; align-items: center; gap: 7px; color: #c4ccd8; font-size: 11.5px; }
  .leg .gl { width: 16px; height: 16px; display: block; }
  .leg .lbl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .leg i { color: #6b7384; font-style: normal; font-size: 10px; font-variant-numeric: tabular-nums; }
  .leg.muted .lbl { color: #8b929e; }
</style>
