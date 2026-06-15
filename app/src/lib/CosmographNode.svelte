<script lang="ts">
  /**
   * Generic Svelte Flow node host for any embedding view.
   *
   * It is context-agnostic: the concrete panel is resolved from the registry by
   * `data.view`, so new contexts render here with no edits (Open/Closed).
   */
  import { NodeResizer, Handle, Position, type NodeProps } from '@xyflow/svelte';
  import { resolvePanel } from './views/registry';

  let { data, selected }: NodeProps = $props();
  const Panel = $derived(resolvePanel(data?.view as string | undefined));
  const title = $derived(data?.title as string | undefined);
</script>

<NodeResizer minWidth={320} minHeight={240} isVisible={selected} color="#7eb6ff" />
<Handle type="target" position={Position.Top} />
<div class="cosmo-node" class:has-title={title}>
  {#if title}
    <!-- drag handle: the title bar moves the node (canvas itself is .nodrag) -->
    <header class="cosmo-title">{title}</header>
  {/if}
  <div class="cosmo-body"><Panel /></div>
</div>

<style>
  .cosmo-node {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    border: 1px solid #232936;
    border-radius: 10px;
    overflow: hidden;
    background: #0b0e14;
    box-shadow: 0 6px 24px rgba(0, 0, 0, .45);
  }

  /* draggable title bar (cursor:move signals the grab handle) */
  .cosmo-title {
    flex: 0 0 auto;
    padding: 7px 12px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .02em;
    color: #e6e9ef;
    background: #141a26;
    border-bottom: 1px solid #232936;
    cursor: move;
    user-select: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cosmo-body {
    flex: 1 1 auto;
    min-height: 0;
    position: relative;
  }
</style>
