/**
 * Sampled view model — representatives over the embedding space.
 *
 * Pure data layer (no Svelte). Overlays the representative samples
 * (`representatives.parquet`: medoid / boundary / outlier roles) onto the fixed
 * umap2 layout (`points.parquet`), each role highlighted by a distinct shape +
 * colour, plus the tag/flag anchors (`anchor_points.parquet`). All "as-is".
 */
import type { CosmographConfig } from '@cosmograph/cosmograph';
import { loadPoints, loadAnchorPoints, loadParquet } from '../../parquet';

export type Role = 'medoid' | 'boundary' | 'outlier';
export type AnchorKind = 'tag' | 'flag';
export type ShapeName = 'circle' | 'square' | 'triangle' | 'diamond' | 'star' | 'cross';

export interface RoleStyle { role: Role; label: string; shape: ShapeName; shapeNum: number; color: string }
export interface AnchorStyle { kind: AnchorKind; label: string; shape: ShapeName; shapeNum: number; color: string }

// One distinct shape + colour per role (PointShape: Triangle=2, Diamond=3, Star=6, Cross=7).
export const ROLE_STYLES: RoleStyle[] = [
  { role: 'medoid',   label: 'Medoid',   shape: 'star',     shapeNum: 6, color: '#7ee787' },
  { role: 'boundary', label: 'Boundary', shape: 'diamond',  shapeNum: 3, color: '#ffb454' },
  { role: 'outlier',  label: 'Outlier',  shape: 'triangle', shapeNum: 2, color: '#ff6e6e' },
];
export const ANCHOR_STYLES: AnchorStyle[] = [
  { kind: 'tag',  label: 'Tag anchor',  shape: 'cross', shapeNum: 7, color: '#7eb6ff' },
  { kind: 'flag', label: 'Flag anchor', shape: 'cross', shapeNum: 7, color: '#d2a8ff' },
];

const SAMPLE_COLOR = '#39414f';   // dim base dots so the highlights pop

export interface SampledModel {
  config: CosmographConfig;
  roleCounts: Record<Role, number>;
  anchorCounts: Record<AnchorKind, number>;
}

type CPoint = {
  sample_id: string; index: number; x: number; y: number;
  kind: string; shape: number; size: number; label: string;
};

export async function buildSampledModel(): Promise<SampledModel> {
  const [pts, anchors, reps] = await Promise.all([
    loadPoints(),
    loadAnchorPoints(),
    loadParquet('./data/representatives.parquet').catch(() => [] as Record<string, unknown>[]),
  ]);

  const xy = new Map<string, { x: number; y: number }>();
  for (const p of pts) xy.set(String(p.sample_id), { x: Number(p.x), y: Number(p.y) });

  let index = 0;

  // base samples: dim circles for context
  const samplePoints: CPoint[] = pts.map((p) => ({
    sample_id: String(p.sample_id), index: index++,
    x: Number(p.x), y: Number(p.y),
    kind: 'sample', shape: 0, size: 5, label: '',
  }));

  // representative markers: distinct shape + colour per role, placed on the same xy
  const roleStyle = new Map(ROLE_STYLES.map((s) => [s.role, s]));
  const roleCounts: Record<Role, number> = { medoid: 0, boundary: 0, outlier: 0 };
  const repPoints: CPoint[] = [];
  for (const r of reps) {
    const role = String(r.role) as Role;
    const st = roleStyle.get(role);
    const pos = xy.get(String(r.sample_id));
    if (!st || !pos) continue;
    roleCounts[role]++;
    repPoints.push({
      sample_id: `rep:${role}:${r.sample_id}:${r.rank ?? roleCounts[role]}`, index: index++,
      x: pos.x, y: pos.y,
      kind: role, shape: st.shapeNum, size: 13, label: '',
    });
  }

  // tag + flag anchors: crosses with persistent name labels
  const anchorStyle = new Map(ANCHOR_STYLES.map((s) => [s.kind, s]));
  const anchorCounts: Record<AnchorKind, number> = { tag: 0, flag: 0 };
  const anchorIds: string[] = [];
  const anchorPoints: CPoint[] = [];
  for (const a of anchors) {
    const kind = String(a.anchor_kind) as AnchorKind;
    const st = anchorStyle.get(kind);
    if (!st) continue;   // skip categories
    anchorCounts[kind]++;
    const id = `anchor:${a.anchor_id}`;
    anchorIds.push(id);
    anchorPoints.push({
      sample_id: id, index: index++,
      x: Number(a.x), y: Number(a.y),
      kind, shape: st.shapeNum, size: 12, label: String(a.anchor_name ?? ''),
    });
  }

  const colorMap: Record<string, string> = {
    sample: SAMPLE_COLOR,
    ...Object.fromEntries(ROLE_STYLES.map((s) => [s.role, s.color])),
    ...Object.fromEntries(ANCHOR_STYLES.map((s) => [s.kind, s.color])),
  };

  const config: CosmographConfig = {
    points: [...samplePoints, ...repPoints, ...anchorPoints],
    pointIdBy: 'sample_id',
    pointIndexBy: 'index',
    pointXBy: 'x',
    pointYBy: 'y',
    enableSimulation: false,
    backgroundColor: '#0b0e14',
    scalePointsOnZoom: true,
    hoveredPointRingColor: '#ffffff',
    pointColorBy: 'kind',
    pointColorStrategy: 'map',
    pointColorByMap: colorMap,
    pointShapeBy: 'shape',
    pointSizeBy: 'size',
    pointSizeByFn: (v: unknown) => Number(v) || 5,
    pointLabelBy: 'label',
    showLabels: true,
    showDynamicLabels: false,
    showTopLabels: false,
    showLabelsFor: anchorIds,           // persistent anchor names only
    pointLabelFontSize: 12,
    pointIncludeColumns: ['*'],
  };

  return { config, roleCounts, anchorCounts };
}
