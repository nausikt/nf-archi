/**
 * `@` provider — navigate/focus a core view panel.
 *
 * Targets are the embedding-view nodes (cosmograph), listed in workflow order
 * via `orderedViews`. Pipeline DAG stages are intentionally excluded for now.
 * Nothing is hard-coded per view — register a new view node and it appears here.
 */
import type { Node } from '@xyflow/svelte';
import type { PaletteItem, PaletteProvider } from './types';
import { orderedViews } from './views';

function label(n: Node): string {
  const d = n.data as { title?: unknown } | undefined;
  return typeof d?.title === 'string' && d.title ? d.title : n.id;
}

function matches(query: string, text: string, id: string): boolean {
  const q = query.trim().toLowerCase();
  return !q || text.toLowerCase().includes(q) || id.toLowerCase().includes(q);
}

export function createNavProvider(
  getNodes: () => Node[],
  focus: (id: string) => void,
): PaletteProvider {
  return {
    trigger: '@',
    title: 'Go to view',
    items: (query: string): PaletteItem[] =>
      orderedViews(getNodes)
        .map((n): PaletteItem => ({ id: n.id, label: label(n), hint: 'view', run: () => focus(n.id) }))
        .filter((it) => matches(query, it.label, it.id)),
  };
}
