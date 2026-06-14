<script lang="ts">
  /**
   * Generic Svelte Flow node host for any embedding view.
   *
   * It is context-agnostic: the concrete panel is resolved from the registry by
   * `data.view`, so new contexts render here with no edits (Open/Closed).
   */
  import { NodeResizer, type NodeProps } from '@xyflow/svelte';
  import { resolvePanel } from './views/registry';

  let { data, selected }: NodeProps = $props();
  const Panel = $derived(resolvePanel(data?.view as string | undefined));
</script>

<NodeResizer minWidth={320} minHeight={240} isVisible={selected} color="#7eb6ff" />
<div class="cosmo-node">
  <Panel />
</div>

<style>
  .cosmo-node {
    width: 100%;
    height: 100%;
    border: 1px solid #232936;
    border-radius: 10px;
    overflow: hidden;
    background: #0b0e14;
    box-shadow: 0 6px 24px rgba(0, 0, 0, .45);
  }
</style>
