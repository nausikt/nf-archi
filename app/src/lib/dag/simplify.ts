/**
 * Graph transforms over a parsed DAG. Kept separate from parsing so the raw
 * mermaid stays faithful and simplification is an opt-in extension point.
 */
import type { DagGraph } from './parse';

/**
 * Collapse Nextflow's anonymous operator nodes (the empty `(( ))` junctions)
 * by bridging each one's predecessors straight to its successors. What remains
 * is the meaningful process + named-channel graph — a readable pipeline DAG.
 */
export function simplify(graph: DagGraph): DagGraph {
  const drop = new Set(
    graph.nodes.filter(n => n.kind === 'junction' || n.label === '').map(n => n.id),
  );
  if (drop.size === 0) return dedupe(graph);

  let edges = graph.edges.map(e => ({ ...e }));
  for (const id of drop) {
    const ins = edges.filter(e => e.target === id);
    const outs = edges.filter(e => e.source === id);
    const bridged = ins.flatMap(i =>
      outs.map(o => ({ source: i.source, target: o.target, label: i.label ?? o.label })),
    );
    edges = edges.filter(e => e.source !== id && e.target !== id).concat(bridged);
  }
  const nodes = graph.nodes.filter(n => !drop.has(n.id));
  return dedupe({ nodes, edges });
}

/** Drop self-loops and duplicate edges (contraction can create both). */
function dedupe(graph: DagGraph): DagGraph {
  const seen = new Set<string>();
  const edges = graph.edges.filter(e => {
    if (e.source === e.target) return false;
    const k = `${e.source}\u0000${e.target}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return { nodes: graph.nodes, edges };
}
