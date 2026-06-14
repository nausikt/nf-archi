/**
 * Embedding-view registry — the single extension point.
 *
 * Map a stable `view` id (set on a Svelte Flow node's `data.view`) to the panel
 * component that renders it. To add a new context (e.g. a co-association graph,
 * a trajectory view), author `views/<ctx>/model.ts` + `views/<ctx>/<Ctx>Panel.svelte`
 * and register it here — the node and canvas stay untouched (Open/Closed).
 */
import type { Component } from 'svelte';
import ReconcilePanel from './reconcile/ReconcilePanel.svelte';

export const DEFAULT_VIEW = 'reconcile';

export const panels: Record<string, Component> = {
  reconcile: ReconcilePanel,
};

export function resolvePanel(view?: string): Component {
  return panels[view ?? DEFAULT_VIEW] ?? panels[DEFAULT_VIEW];
}
