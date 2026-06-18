/**
 * Core-view ordering — the single source of truth for "which panels are
 * navigable and in what order".
 *
 * Views are the cosmograph nodes; their left-to-right layout already encodes the
 * pipeline/workflow order (reduce·cluster grid -> explore -> sampled), so we
 * derive the sequence from `position.x` rather than hard-coding a list. DAG
 * stage nodes are intentionally excluded.
 */
import type { Node } from '@xyflow/svelte';

export function isView(n: Node): boolean {
  return n.type === 'cosmograph';
}

/** Views sorted in workflow order (x, then y as a tie-breaker). */
export function orderedViews(getNodes: () => Node[]): Node[] {
  return getNodes()
    .filter(isView)
    .sort((a, b) => a.position.x - b.position.x || a.position.y - b.position.y);
}
