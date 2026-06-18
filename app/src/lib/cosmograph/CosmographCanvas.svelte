<script lang="ts">
  /**
   * Generic, context-agnostic Cosmograph host.
   *
   * Single responsibility: own the Cosmograph instance lifecycle (create from a
   * config, fit the view once data is uploaded, tear down on unmount) and provide
   * a positioned container into which a context-specific overlay can render.
   *
   * It knows nothing about tags, anchors, explore, etc. Context views supply a
   * `config` and read back the live instance through `bind:cosmo`.
   */
  import { Cosmograph, type CosmographConfig } from '@cosmograph/cosmograph';
  import { untrack, type Snippet } from 'svelte';

  let {
    config,
    cosmo = $bindable(),
    children,
  }: {
    config?: CosmographConfig;
    cosmo?: Cosmograph;
    children?: Snippet;
  } = $props();

  let el: HTMLDivElement;
  let instance = $state<Cosmograph>();
  let builtConfig: CosmographConfig | undefined;   // the config the constructor used
  const ready = $derived(!!config);                // boolean: flips false->true once

  // Create the instance ONCE. Must NOT read `instance` here: writing it below
  // would re-trigger this effect -> destroy/recreate loop (blank canvas).
  $effect(() => {
    if (!el || !ready) return;
    const cfg = untrack(() => config)!;
    const inst = new Cosmograph(el, cfg);
    builtConfig = cfg;
    instance = inst;
    inst.dataUploaded().then(() => { if (instance === inst) { inst.fitView(0); cosmo = inst; } });
    return () => {
      void inst.destroy?.();
      if (instance === inst) { instance = undefined; cosmo = undefined; }
    };
  });

  // Recolor / swap data IN PLACE on later config changes — recreating the
  // instance leaves a blank canvas and leaks WebGL contexts. Explore's config
  // never changes (c === builtConfig), so it stays a pure create-once.
  $effect(() => {
    const c = config;
    const inst = instance;
    if (!inst || !c || c === builtConfig) return;
    let alive = true;
    inst.setConfig(c).then(() => { if (alive) inst.fitView(0); }).catch(() => { /* noop */ });
    return () => { alive = false; };
  });
</script>

<!-- nopan/nodrag/nowheel: let Cosmograph own pan/zoom/click on the canvas instead
     of Svelte Flow's pane (without nopan the pane eats the mousedown -> no click). -->
<div class="canvas-root">
  <div class="cosmo nodrag nopan nowheel" bind:this={el}></div>
  {@render children?.()}
</div>

<style>
  .canvas-root {
    position: relative;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    background: #0b0e14;
    color: #e6e9ef;
  }
  .cosmo { position: absolute; inset: 0; background: #0b0e14; }
  .cosmo :global(canvas) { display: block; }
</style>
