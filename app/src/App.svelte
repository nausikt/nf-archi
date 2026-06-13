<script lang="ts">
  import { SvelteFlow, Background, Controls, type Node, type Edge } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css'; // required, or nodes render unstyled

  let nodes = $state<Node[]>([
    { id: 'embed',    position: { x: 0,   y: 0   }, data: { label: 'embeddings' } },
    { id: 'cluster',  position: { x: 220, y: 80  }, data: { label: 'clusters' } },
    { id: 'ensemble', position: { x: 440, y: 160 }, data: { label: 'consensus' } },
  ]);
  let edges = $state<Edge[]>([
    { id: 'e1', source: 'embed',   target: 'cluster' },
    { id: 'e2', source: 'cluster', target: 'ensemble' },
  ]);
</script>

<SvelteFlow bind:nodes bind:edges fitView>
  <Background />
  <Controls />
</SvelteFlow>
