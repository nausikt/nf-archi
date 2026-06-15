/**
 * Dependency-free layered (Sugiyama-lite) layout: longest-path layering with a
 * stable in-layer order. Good enough for the modest pipeline DAGs here and keeps
 * the bundle lean (no dagre/elk). Swap in a richer engine later behind this
 * same `(graph) -> positions` contract.
 */
import type { DagGraph } from './parse';

export interface XY { x: number; y: number; }

export interface LayoutOpts {
  dir?: 'LR' | 'TB';
  gapMain?: number;    // spacing between layers
  gapCross?: number;   // spacing within a layer
}

export function layeredLayout(graph: DagGraph, opts: LayoutOpts = {}): Map<string, XY> {
  const dir = opts.dir ?? 'LR';
  const gapMain = opts.gapMain ?? 260;
  const gapCross = opts.gapCross ?? 104;

  const ids = graph.nodes.map(n => n.id);
  const indeg = new Map(ids.map(id => [id, 0]));
  const succ = new Map<string, string[]>(ids.map(id => [id, []]));
  for (const e of graph.edges) {
    if (!indeg.has(e.source) || !indeg.has(e.target)) continue;
    succ.get(e.source)!.push(e.target);
    indeg.set(e.target, indeg.get(e.target)! + 1);
  }

  // Kahn topological sweep; layer = max(predecessor layer) + 1.
  const layer = new Map(ids.map(id => [id, 0]));
  const deg = new Map(indeg);
  const queue = ids.filter(id => deg.get(id) === 0);
  const placed = new Set<string>();
  const order: string[] = [];
  while (queue.length) {
    const u = queue.shift()!;
    order.push(u);
    placed.add(u);
    for (const v of succ.get(u)!) {
      layer.set(v, Math.max(layer.get(v)!, layer.get(u)! + 1));
      deg.set(v, deg.get(v)! - 1);
      if (deg.get(v) === 0) queue.push(v);
    }
  }
  for (const id of ids) if (!placed.has(id)) order.push(id);   // cycle fallback

  // Bucket by layer in topo order (stable cross-axis ordering).
  const byLayer = new Map<number, string[]>();
  for (const id of order) {
    const l = layer.get(id)!;
    const bucket = byLayer.get(l) ?? byLayer.set(l, []).get(l)!;
    bucket.push(id);
  }

  const pos = new Map<string, XY>();
  for (const [l, members] of [...byLayer.entries()].sort((a, b) => a[0] - b[0])) {
    members.forEach((id, i) => {
      const cross = (i - (members.length - 1) / 2) * gapCross;
      const main = l * gapMain;
      pos.set(id, dir === 'LR' ? { x: main, y: cross } : { x: cross, y: main });
    });
  }
  return pos;
}
