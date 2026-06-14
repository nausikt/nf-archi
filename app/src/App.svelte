<script lang="ts">
  import { SvelteFlow, Background, Controls, type Node, type Edge, type NodeTypes } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css'; // required, or nodes render unstyled
  import CosmographNode from './lib/CosmographNode.svelte';

  const nodeTypes: NodeTypes = { cosmograph: CosmographNode };

  // Pipeline graph + a resizable Cosmograph node living inside the flow.
  let nodes = $state<Node[]>([
    { id: 'embed',    position: { x: 0,   y: 0   }, data: { label: 'embeddings' } },
    { id: 'reduce',   position: { x: 200, y: 60  }, data: { label: 'reduce (umap2)' } },
    { id: 'cluster',  position: { x: 400, y: 120 }, data: { label: 'clusters' } },
    { id: 'ensemble', position: { x: 600, y: 180 }, data: { label: 'consensus' } },
    {
      id: 'umap',
      type: 'cosmograph',
      position: { x: 120, y: 300 },
      width: 1000,
      height: 640,
      data: { view: 'reconcile' },   // After Ensemble · Reconcile embedding view
    },
  ]);
  let edges = $state<Edge[]>([
    { id: 'e1', source: 'embed',    target: 'reduce' },
    { id: 'e2', source: 'reduce',   target: 'cluster' },
    { id: 'e3', source: 'cluster',  target: 'ensemble' },
    { id: 'e4', source: 'ensemble', target: 'umap' },
  ]);
</script>

<div class="workbench">
  <SvelteFlow bind:nodes bind:edges {nodeTypes} colorMode="dark" fitView>
    <Background />
    <Controls />
  </SvelteFlow>
</div>

<style>
  .workbench {
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    background: #0b0e14;
  }
</style>
