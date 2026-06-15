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
  import type { Snippet } from 'svelte';

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

  $effect(() => {
    if (!el || !config) return;
    let alive = true;
    let instance: Cosmograph | undefined;
    (async () => {
      instance = new Cosmograph(el, config);
      await instance.dataUploaded();
      if (!alive) { void instance.destroy?.(); return; }
      instance.fitView(0);
      cosmo = instance;
    })();
    return () => {
      alive = false;
      void instance?.destroy?.();
      cosmo = undefined;
    };
  });
</script>

<div class="canvas-root">
  <div class="cosmo nodrag nowheel" bind:this={el}></div>
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
