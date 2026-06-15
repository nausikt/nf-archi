<script lang="ts">
  /**
   * Custom Svelte Flow node for an auto-generated DAG element.
   *
   * Purely presentational: kind (`process` | `io` | `operator`) drives styling,
   * `group` shows the originating sub-workflow. Handles flip with layout `dir`.
   */
  import { Handle, Position, type NodeProps } from '@xyflow/svelte';

  let { data }: NodeProps = $props();

  const kind = $derived((data?.kind as string) ?? 'process');
  const label = $derived((data?.label as string) ?? '');
  const group = $derived(data?.group as string | undefined);
  const tb = $derived(data?.dir === 'TB');
</script>

<div class="dag-node {kind}" title={group ? `${group} · ${label}` : label}>
  <Handle type="target" position={tb ? Position.Top : Position.Left} />
  {#if group}<span class="grp">{group}</span>{/if}
  <span class="lbl">{label}</span>
  <Handle type="source" position={tb ? Position.Bottom : Position.Right} />
</div>

<style>
  .dag-node {
    box-sizing: border-box;
    min-width: 116px;
    max-width: 200px;
    padding: 8px 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    border-radius: 8px;
    border: 1px solid #2a3140;
    background: #161b26;
    color: #e6e9ef;
    font-size: 12px;
    line-height: 1.25;
    text-align: center;
  }

  /* processes — the work; brightest, accented */
  .dag-node.process {
    border-color: #3b6ea5;
    background: #18283c;
    font-weight: 600;
  }

  /* named channels / values — data artifacts; dashed + dimmer */
  .dag-node.io {
    border-style: dashed;
    border-color: #4a5568;
    background: #12161f;
    color: #aab4c5;
    font-size: 11px;
  }

  /* leftover operators — subtle */
  .dag-node.operator {
    border-color: #2a3140;
    background: #12161f;
    color: #8b94a7;
  }

  .grp {
    font-size: 9px;
    letter-spacing: .04em;
    text-transform: uppercase;
    color: #7eb6ff;
    opacity: .8;
  }
  .io .grp,
  .operator .grp { color: #6b7689; }

  .lbl {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :global(.dag-node .svelte-flow__handle) {
    width: 7px;
    height: 7px;
    background: #6b7689;
    border: none;
  }
</style>
