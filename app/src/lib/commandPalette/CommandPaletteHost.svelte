<script lang="ts">
  /**
   * Composition root for view navigation.
   *
   * Must live *inside* <SvelteFlow> to read the flow instance via
   * `useSvelteFlow()`. It wires:
   *   - the `@` command palette (Cmd/Ctrl+Shift+P) to focus any view, and
   *   - Shift + Left/Right to step through the core views in workflow order.
   * Both share a single "cursor" (`current`) so the two stay in sync.
   */
  import { useSvelteFlow } from '@xyflow/svelte';
  import CommandPalette from './CommandPalette.svelte';
  import { createNavProvider } from './navProvider';
  import { orderedViews } from './views';
  import type { PaletteProvider } from './types';

  const { getNodes, fitView } = useSvelteFlow();

  let current = $state(0);

  function centerOn(id: string) {
    void fitView({ nodes: [{ id }], duration: 600, padding: 0.3, maxZoom: 1.1 });
  }

  // focus a specific view (from the palette) and remember it as the cursor
  function focusView(id: string) {
    const idx = orderedViews(getNodes).findIndex((v) => v.id === id);
    if (idx >= 0) current = idx;
    centerOn(id);
  }

  // step through core views in workflow order (clamped at the ends)
  function step(delta: number) {
    const views = orderedViews(getNodes);
    if (!views.length) return;
    current = Math.max(0, Math.min(views.length - 1, current + delta));
    centerOn(views[current].id);
  }

  function onWindowKey(e: KeyboardEvent) {
    if (!e.shiftKey || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const t = e.target as HTMLElement | null;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    e.preventDefault();
    step(e.key === 'ArrowRight' ? 1 : -1);
  }

  const providers: PaletteProvider[] = [createNavProvider(getNodes, focusView)];
</script>

<svelte:window onkeydown={onWindowKey} />
<CommandPalette {providers} />
