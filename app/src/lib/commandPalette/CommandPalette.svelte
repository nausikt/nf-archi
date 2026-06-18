<script lang="ts">
  /**
   * Generic command-palette overlay (Cmd/Ctrl + Shift + P).
   *
   * It is view-agnostic: it renders whatever `providers` it is given and runs the
   * selected item's `run()`. The active provider is chosen by the input's leading
   * trigger char (e.g. `@`), so typing `@umap` filters that provider's items.
   */
  import type { PaletteItem, PaletteProvider } from './types';

  let { providers }: { providers: PaletteProvider[] } = $props();

  let open = $state(false);
  let query = $state('');
  let active = $state(0);
  let inputEl = $state<HTMLInputElement | null>(null);

  const byTrigger = $derived(new Map(providers.map((p) => [p.trigger, p])));
  const provider = $derived(query.length ? byTrigger.get(query[0]) : undefined);
  const items = $derived(provider ? provider.items(query.slice(1)) : []);

  // keep the highlighted row in range as the list shrinks/grows
  $effect(() => {
    if (active > items.length - 1) active = items.length ? items.length - 1 : 0;
  });

  function openPalette() {
    open = true;
    query = '';
    active = 0;
    queueMicrotask(() => inputEl?.focus());
  }

  function close() {
    open = false;
  }

  function onWindowKey(e: KeyboardEvent) {
    const isToggle = (e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p';
    if (isToggle) {
      e.preventDefault();
      open ? close() : openPalette();
    } else if (open && e.key === 'Escape') {
      e.preventDefault();
      close();
    }
  }

  function onInputKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      active = Math.min(active + 1, items.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      active = Math.max(active - 1, 0);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      select(items[active]);
    }
  }

  function select(item?: PaletteItem) {
    if (!item) return;
    item.run();
    close();
  }
</script>

<svelte:window onkeydown={onWindowKey} />

{#if open}
  <div class="cp-backdrop" role="presentation" onmousedown={close}>
    <div class="cp" role="dialog" aria-modal="true" onmousedown={(e) => e.stopPropagation()}>
      <input
        bind:this={inputEl}
        bind:value={query}
        class="cp-input"
        placeholder="Type @ to go to a panel…"
        spellcheck="false"
        autocomplete="off"
        onkeydown={onInputKey}
      />

      {#if !provider}
        <ul class="cp-list">
          {#each providers as p (p.trigger)}
            <li class="cp-row cp-hint"><kbd>{p.trigger}</kbd><span>{p.title}</span></li>
          {/each}
        </ul>
      {:else if items.length}
        <ul class="cp-list">
          {#each items as item, i (item.id)}
            <li
              class="cp-row"
              class:active={i === active}
              onmouseenter={() => (active = i)}
              onmousedown={() => select(item)}
            >
              <span class="cp-label">{item.label}</span>
              {#if item.hint}<span class="cp-tag">{item.hint}</span>{/if}
            </li>
          {/each}
        </ul>
      {:else}
        <div class="cp-empty">No matches</div>
      {/if}
    </div>
  </div>
{/if}

<style>
  /* Spotlight-like: large, centered-high, translucent vibrancy panel. */
  .cp-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 16vh;
    background: rgba(4, 6, 10, 0.28);
  }

  .cp {
    width: min(760px, 90vw);
    background: rgba(28, 32, 42, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55);
    -webkit-backdrop-filter: blur(28px) saturate(180%);
    backdrop-filter: blur(28px) saturate(180%);
    overflow: hidden;
  }

  .cp-input {
    width: 100%;
    box-sizing: border-box;
    padding: 20px 24px;
    font-size: 24px;
    font-weight: 300;
    letter-spacing: 0.01em;
    color: #f4f6fa;
    background: transparent;
    border: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    outline: none;
  }
  .cp-input::placeholder { color: rgba(235, 238, 245, 0.4); }

  .cp-list {
    list-style: none;
    margin: 0;
    padding: 8px;
    max-height: 52vh;
    overflow-y: auto;
  }

  .cp-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 12px;
    cursor: pointer;
    color: #dde2ec;
    font-size: 15px;
  }
  .cp-row.active { background: rgba(126, 182, 255, 0.22); color: #fff; }

  .cp-label { flex: 1 1 auto; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .cp-tag {
    flex: 0 0 auto;
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #aaccff;
    background: rgba(126, 182, 255, 0.16);
    padding: 3px 9px;
    border-radius: 999px;
  }

  .cp-hint { cursor: default; color: rgba(235, 238, 245, 0.6); }
  .cp-hint kbd {
    font: inherit;
    color: #f4f6fa;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 7px;
    padding: 2px 9px;
  }

  .cp-empty { padding: 20px 24px; color: rgba(235, 238, 245, 0.45); font-size: 15px; }
</style>
