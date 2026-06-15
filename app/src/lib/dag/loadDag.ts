/**
 * Turn a Nextflow mermaid DAG into Svelte Flow nodes/edges.
 *
 * Pipeline: fetch `.mmd` -> parse -> simplify (drop junctions) -> layered layout
 * -> Svelte Flow graph. The DAG nodes use the `dag` node type (see DagNode.svelte).
 */
import type { Node, Edge } from '@xyflow/svelte';
import { parseMermaid } from './parse';
import { simplify } from './simplify';
import { layeredLayout, type LayoutOpts } from './layout';

export interface DagFlow {
  nodes: Node[];
  edges: Edge[];
}

export function toFlow(text: string, opts: LayoutOpts = { dir: 'LR' }): DagFlow {
  const graph = simplify(parseMermaid(text));
  const pos = layeredLayout(graph, opts);

  const nodes: Node[] = graph.nodes.map(n => ({
    id: n.id,
    type: 'dag',
    position: pos.get(n.id) ?? { x: 0, y: 0 },
    data: { label: n.label || n.id, kind: n.kind, group: n.group, dir: opts.dir ?? 'LR' },
  }));

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e${i}_${e.source}_${e.target}`,
    source: e.source,
    target: e.target,
    label: e.label,
  }));

  return { nodes, edges };
}

/** Fetch + convert the published DAG; null when no run has produced one yet. */
export async function loadDag(
  base = './data',
  file = 'pipeline_dag.mmd',
  opts: LayoutOpts = { dir: 'LR' },
): Promise<DagFlow | null> {
  const res = await fetch(`${base}/${file}`);
  if (!res.ok) return null;
  return toFlow(await res.text(), opts);
}
