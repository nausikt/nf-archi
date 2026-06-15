/**
 * Reduce · Clustering grid view model — the hyperparameter-sweep context.
 *
 * Pure data layer (no Svelte). The reduce/cluster grid is enumerated from the
 * `member_weights.json` manifest the ensemble already emits (one row per
 * reduction × clustering member, with metrics). Each member's `run` id encodes
 * its knobs (parsed here), and maps 1:1 to `clusters/cluster_<run>.parquet`.
 *
 * Positions come from the single 2D viz space (`umap2.parquet`) — the only 2D
 * coords available — so scrubbing knobs recolors the same map by that member's
 * partition. Loading is "as-is": files are read straight from ./data.
 */
import type { CosmographConfig } from '@cosmograph/cosmograph';
import { loadParquet } from '../../parquet';

const MANIFEST = './data/member_weights.json';
const VIZ = './data/umap2.parquet';
const RUN_DIR = './data/clusters';

/** One grid member: parsed knobs + the metrics carried in the manifest. */
export interface Member {
  run: string;
  algorithm: string;
  // reduction knobs
  pca?: number;
  n_components?: number;
  n_neighbors?: number;
  min_dist?: number;
  // clustering knobs
  min_cluster_size?: number;
  min_samples?: number | null;
  k?: number;
  linkage?: string;
  metric?: string;
  // metrics (from manifest)
  n_clusters: number;
  noise: number;
  noise_fraction: number;
  silhouette: number;
  final_weight: number;
  dropped: boolean;
}

export interface BasePoint { sample_id: string; x: number; y: number; index: number; }

export interface ClusterBin { label: number; color: string; count: number; }

export interface RunView { config: CosmographConfig; clusters: ClusterBin[] }

const PALETTE = ['#7eb6ff', '#ffb454', '#ff6e6e', '#5fe3d0', '#7ee787',
                 '#ffd866', '#d2a8ff', '#ff9ecd', '#c9a98b', '#a0d8ff',
                 '#ffcf8b', '#ff9b9b', '#8df0e2', '#a9f0ad', '#e3c4ff'];
const NOISE_COLOR = '#3a4150';

/** Parse `pca50_n10_nn10_md00__hdbscan_mcs3_ms5` into its hyperparameter knobs. */
export function parseRun(run: string): Partial<Member> {
  const [red = '', clu = ''] = run.split('__');
  const k: Partial<Member> = {};

  for (const tok of red.split('_')) {
    let m: RegExpMatchArray | null;
    if ((m = tok.match(/^pca(\d+)$/))) k.pca = +m[1];
    else if ((m = tok.match(/^n(\d+)$/))) k.n_components = +m[1];
    else if ((m = tok.match(/^nn(\d+)$/))) k.n_neighbors = +m[1];
    else if ((m = tok.match(/^md(\d+)$/))) k.min_dist = +m[1] / 10;   // md00->0.0, md01->0.1
  }

  const ct = clu.split('_');
  k.algorithm = ct[0] || 'unknown';
  for (const tok of ct.slice(1)) {
    let m: RegExpMatchArray | null;
    if ((m = tok.match(/^mcs(\d+)$/))) k.min_cluster_size = +m[1];
    else if ((m = tok.match(/^ms(\d+)$/))) k.min_samples = +m[1];
    else if ((m = tok.match(/^k(\d+)$/))) k.k = +m[1];
    else if ((m = tok.match(/^lk(.+)$/))) k.linkage = m[1];
    else if ((m = tok.match(/^m(.+)$/))) k.metric = m[1];
  }
  // hdbscan with no explicit min_samples is a real, distinct setting (null)
  if (k.algorithm === 'hdbscan' && k.min_samples === undefined) k.min_samples = null;
  return k;
}

/** Load + parse the grid manifest into members (highest silhouette first). */
export async function loadMembers(): Promise<Member[]> {
  const res = await fetch(MANIFEST);
  if (!res.ok) throw new Error('member_weights.json not found — run the pipeline first');
  const raw = (await res.json()) as Record<string, unknown>[];
  const members = raw.map((r) => {
    const run = String(r.run);
    return {
      ...parseRun(run),
      run,
      algorithm: String(r.algorithm ?? parseRun(run).algorithm),
      n_clusters: Number(r.n_clusters ?? 0),
      noise: Number(r.noise ?? 0),
      noise_fraction: Number(r.noise_fraction ?? 0),
      silhouette: Number(r.silhouette ?? 0),
      final_weight: Number(r.final_weight ?? 0),
      dropped: Boolean(r.dropped),
    } as Member;
  });
  return members.sort((a, b) => b.silhouette - a.silhouette);
}

/** Load the fixed 2D viz coordinates that every member is rendered onto. */
export async function loadBasePoints(): Promise<BasePoint[]> {
  const rows = await loadParquet(VIZ);
  return rows.map((r, index) => ({
    sample_id: String(r.sample_id),
    x: Number(r.x),
    y: Number(r.y),
    index,
  }));
}

/** Load a single member's per-sample cluster labels. */
export async function loadRunLabels(run: string): Promise<Map<string, number>> {
  const rows = await loadParquet(`${RUN_DIR}/cluster_${run}.parquet`);
  const m = new Map<string, number>();
  for (const r of rows) m.set(String(r.sample_id), Number(r.label));
  return m;
}

/** Build the Cosmograph config + legend for a member, coloring the viz by labels. */
export function buildRunView(base: BasePoint[], labels: Map<string, number>): RunView {
  const counts = new Map<number, number>();
  for (const p of base) {
    const l = labels.get(p.sample_id) ?? -1;
    counts.set(l, (counts.get(l) ?? 0) + 1);
  }
  const ordered = [...counts.keys()].sort((a, b) => a - b);
  const colorByMap: Record<string, string> = {};
  let ci = 0;
  for (const l of ordered) colorByMap[String(l)] = l < 0 ? NOISE_COLOR : PALETTE[ci++ % PALETTE.length];

  const points = base.map((p) => {
    const l = labels.get(p.sample_id) ?? -1;
    return { sample_id: p.sample_id, index: p.index, x: p.x, y: p.y, cluster: String(l), is_noise: l < 0 ? 1 : 0 };
  });

  const config: CosmographConfig = {
    points,
    pointIdBy: 'sample_id',
    pointIndexBy: 'index',
    pointXBy: 'x',
    pointYBy: 'y',
    enableSimulation: false,
    backgroundColor: '#0b0e14',
    scalePointsOnZoom: true,
    hoveredPointRingColor: '#ffffff',
    pointGreyoutColor: '#2b3340',
    pointGreyoutOpacity: 0.25,
    pointColorBy: 'cluster',
    pointColorStrategy: 'map',
    pointColorByMap: colorByMap,
    pointSizeBy: 'is_noise',
    pointSizeByFn: (v: unknown) => (Number(v) ? 4 : 7),   // noise smaller
    pointIncludeColumns: ['*'],
  };

  const clusters: ClusterBin[] = ordered.map((label) => ({
    label, color: colorByMap[String(label)], count: counts.get(label) ?? 0,
  }));
  return { config, clusters };
}

// ---- knob axes (derived from the available members) ----

export type KnobKey = 'n_components' | 'n_neighbors' | 'algorithm' | 'min_cluster_size' | 'min_samples' | 'k';
export type KnobValue = number | string | null;
export interface Axis { key: KnobKey; title: string; values: KnobValue[] }

const AXIS_DEFS: { key: KnobKey; title: string }[] = [
  { key: 'n_components',     title: 'n_components' },
  { key: 'n_neighbors',      title: 'n_neighbors' },
  { key: 'algorithm',        title: 'algorithm' },
  { key: 'min_cluster_size', title: 'min_cluster_size' },
  { key: 'min_samples',      title: 'min_samples' },
  { key: 'k',                title: 'k' },
];

/** Distinct, sorted values per knob across members (only axes that vary). */
export function buildAxes(members: Member[]): Axis[] {
  return AXIS_DEFS.map(({ key, title }) => {
    const nums = new Set<number>();
    const strs = new Set<string>();
    let hasNull = false;
    for (const m of members) {
      const v = m[key];
      if (v === undefined) continue;
      if (v === null) hasNull = true;
      else if (typeof v === 'number') nums.add(v);
      else strs.add(String(v));
    }
    const values: KnobValue[] = [
      ...[...nums].sort((a, b) => a - b),
      ...[...strs].sort((a, b) => a.localeCompare(b)),
    ];
    if (hasNull) values.push(null);
    return { key, title, values };
  }).filter((a) => a.values.length > 0);
}

/** Members matching the currently selected knobs (unset knobs are wildcards). */
export function filterMembers(members: Member[], sel: Partial<Record<KnobKey, KnobValue>>): Member[] {
  const keys = Object.keys(sel) as KnobKey[];
  return members.filter((m) => keys.every((k) => sel[k] === undefined || m[k] === sel[k]));
}
