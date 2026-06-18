/**
 * Command-palette abstractions — the extension surface.
 *
 * The palette UI depends only on these interfaces, never on concrete views or
 * the flow instance (Dependency Inversion). New capabilities are added by
 * registering another `PaletteProvider` keyed by a trigger char (Open/Closed):
 * e.g. `@` to focus a panel, `>` to run a command, `#` to jump to a tag.
 */

/** A single selectable row produced by a provider. */
export interface PaletteItem {
  /** Stable id (used as the keyed-each key). */
  id: string;
  /** Primary text shown to the user. */
  label: string;
  /** Optional right-aligned secondary tag (e.g. "view" | "stage"). */
  hint?: string;
  /** Action invoked when the item is chosen. */
  run: () => void;
}

/** A source of items, activated when the input begins with `trigger`. */
export interface PaletteProvider {
  /** Leading character that selects this provider (e.g. '@'). */
  trigger: string;
  /** Human label shown as a mode hint (e.g. "Go to panel"). */
  title: string;
  /** Items matching `query` (the input text after the trigger char). */
  items: (query: string) => PaletteItem[];
}
