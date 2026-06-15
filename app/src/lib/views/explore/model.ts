/**
 * Explore view model — the UMAP2 embedding-space exploration context.
 *
 * Pure data layer (no Svelte): turns the pipeline parquet outputs into a ready
 * Cosmograph config plus the derived view model (points, tag colors) the overlay
 * UI needs. Kept framework-free so it is trivially testable and so new contexts
 * can be authored by copying this file rather than editing the panel/canvas.
 */
import type { CosmographConfig } from '@cosmograph/cosmograph';
import {
  loadPoints, loadPrelabels, loadAnchorPoints, type PrelabelRow,
} from '../../parquet';

/** Enriched sample point: points.parquet row + many-to-many arrays + index. */
export type Pt = {
  sample_id: string;
  consensus_label?: number;
  top_category?: string;
  top_tag?: string;
  tags: string[];
  flags: string[];
  index: number;
  [k: string]: unknown;
};

export interface ExploreModel {
  config: CosmographConfig;
  pts: Pt[];
  tagColor: Map<string, string>;
  hasTag: boolean;
}

// bright, high-contrast categorical palette for a dark canvas
const PALETTE = ['#7eb6ff', '#ffb454', '#ff6e6e', '#5fe3d0', '#7ee787',
                 '#ffd866', '#d2a8ff', '#ff9ecd', '#c9a98b', '#a0d8ff',
                 '#ffcf8b', '#ff9b9b', '#8df0e2', '#a9f0ad', '#e3c4ff'];

/** group prelabels -> Map<sample_id, names[] ordered by rank> for a kind */
function arraysByKind(pre: PrelabelRow[], kind: string): Map<string, string[]> {
  const tmp = new Map<string, { name: string; rank: number }[]>();
  for (const r of pre) {
    if (r.anchor_kind !== kind || !r.anchor_name) continue;
    const sid = String(r.sample_id);
    (tmp.get(sid) ?? tmp.set(sid, []).get(sid)!).push({ name: String(r.anchor_name), rank: Number(r.rank) });
  }
  const out = new Map<string, string[]>();
  for (const [sid, arr] of tmp) out.set(sid, arr.sort((a, b) => a.rank - b.rank).map((x) => x.name));
  return out;
}

export async function buildExploreModel(): Promise<ExploreModel> {
  const [data, pre, anchorRows] = await Promise.all([
    loadPoints(), loadPrelabels(), loadAnchorPoints(),
  ]);

  const tagMap = arraysByKind(pre, 'tag');
  const flagMap = arraysByKind(pre, 'flag');

  // stable tag colors in order of first appearance of the rank-1 tag
  const tagColor = new Map<string, string>();
  let ci = 0;
  for (const r of data) {
    const k = r.top_tag as string | undefined;
    if (k && !tagColor.has(k)) tagColor.set(k, PALETTE[ci++ % PALETTE.length]);
  }

  const pts: Pt[] = data.map((r, index) => ({
    ...(r as object),
    sample_id: String(r.sample_id),
    tags: tagMap.get(String(r.sample_id)) ?? (r.top_tag ? [String(r.top_tag)] : []),
    flags: flagMap.get(String(r.sample_id)) ?? (r.top_flag ? [String(r.top_flag)] : []),
    index,
  })) as Pt[];

  const hasTag = pts.length > 0 && !!pts[0].top_tag;

  // tag anchors -> overlay markers; ensure each has a colour in the tag map
  const anchors = anchorRows.filter((a) => a.anchor_kind === 'tag' && a.anchor_name);
  for (const a of anchors) {
    const k = String(a.anchor_name);
    if (!tagColor.has(k)) tagColor.set(k, PALETTE[ci++ % PALETTE.length]);
  }
  const colorMap = Object.fromEntries(tagColor); // string keys -> legend enumerates

  // Cosmograph can't ingest array-valued columns from plain objects, so feed it
  // scalars only; many-to-many search works via substring over the joined strings.
  // samples = circle (shape 0); anchors = cross (shape 7) with a persistent label.
  const samplePoints = pts.map(({ tags, flags, ...rest }) => ({
    ...rest,
    tags_all: tags.join(', '),
    flags_all: flags.join(', '),
    is_anchor: 0,
    shape: 0,
    label: '',
  }));
  // anchors must share the exact sample schema or DuckDB rejects the table
  const blank = Object.fromEntries(
    Object.keys(samplePoints[0] ?? {}).map((k) => [k, null]),
  );
  const anchorPoints = anchors.map((a, i) => ({
    ...blank,
    sample_id: `anchor:${a.anchor_id}`,
    x: a.x, y: a.y,
    top_tag: String(a.anchor_name),     // colour by the tag it represents
    tags_all: '', flags_all: '',
    is_anchor: 1,
    shape: 7,                           // Cross marker
    label: String(a.anchor_name),
    index: pts.length + i,
  }));
  const cosmoPoints = [...samplePoints, ...anchorPoints];
  const anchorIds = anchorPoints.map((a) => a.sample_id);

  const config: CosmographConfig = {
    points: cosmoPoints,
    pointIdBy: 'sample_id',
    pointIndexBy: 'index',
    pointXBy: 'x',
    pointYBy: 'y',
    enableSimulation: false,
    backgroundColor: '#0b0e14',
    pointSizeScale: 1,
    scalePointsOnZoom: true,
    hoveredPointRingColor: '#ffffff',
    pointGreyoutColor: '#2b3340',
    pointGreyoutOpacity: 0.25,
    pointColorBy: hasTag ? 'top_tag' : undefined,        // colour by dominant tag
    pointColorStrategy: hasTag ? 'map' : undefined,
    pointColorByMap: hasTag ? colorMap : undefined,
    pointShapeBy: 'shape',
    pointSizeBy: 'is_anchor',
    pointSizeByFn: (v: unknown) => (Number(v) ? 13 : 6),  // anchors larger
    pointLabelBy: 'label',
    showLabels: true,
    showDynamicLabels: false,
    showTopLabels: false,
    showLabelsFor: anchorIds,                            // persistent anchor names only
    pointLabelFontSize: 12,
    pointIncludeColumns: ['*'],
  };

  return { config, pts, tagColor, hasTag };
}

// ---- derived view-model helpers (pure; consumed by the panel via $derived) ----

export type Bin = { value: string; count: number; indices: number[]; color?: string };

export function summarize(pts: Pt[]) {
  const labels = pts.map((r) => Number(r.consensus_label));
  const clusters = new Set(labels.filter((n) => Number.isFinite(n) && n >= 0));
  const noise = labels.filter((n) => !Number.isFinite(n) || n < 0).length;
  return { points: pts.length, clusters: clusters.size, noise };
}

function toBins(m: Map<string, number[]>, tagColor?: Map<string, string>): Bin[] {
  return [...m.entries()]
    .map(([value, indices]) => ({
      value, indices, count: indices.length,
      color: tagColor?.get(value),
    }))
    .sort((a, b) => b.count - a.count);
}

/** distribution over a single string field (one value per point) */
export function distSingle(pts: Pt[], field: keyof Pt): Bin[] {
  const m = new Map<string, number[]>();
  pts.forEach((r, i) => {
    const v = r[field];
    if (v == null || v === '') return;
    const k = String(v);
    (m.get(k) ?? m.set(k, []).get(k)!).push(i);
  });
  return toBins(m);
}

/** distribution over an array field (many-to-many: a point counts in each value) */
export function distMulti(pts: Pt[], field: 'tags' | 'flags', tagColor?: Map<string, string>): Bin[] {
  const m = new Map<string, number[]>();
  pts.forEach((r, i) => {
    for (const v of r[field]) {
      if (!v) continue;
      (m.get(v) ?? m.set(v, []).get(v)!).push(i);
    }
  });
  return toBins(m, tagColor);
}
