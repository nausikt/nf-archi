import { parquetReadObjects } from 'hyparquet';
import { compressors } from 'hyparquet-compressors';

export interface PointRow {
  sample_id: string;
  x: number;
  y: number;
  consensus_label?: number;
  stability?: number;
  [k: string]: unknown;
}

/** Fetch + parse a parquet file into plain row objects; null if the file is absent. */
async function tryLoad(url: string): Promise<Record<string, unknown>[] | null> {
  const res = await fetch(url);
  if (!res.ok) return null;
  const file = await res.arrayBuffer();
  return parquetReadObjects({ file, compressors });   // snappy etc. handled by compressors
}

/** Fetch + parse a parquet file by URL; throws if the file is absent. */
export async function loadParquet(url: string): Promise<Record<string, unknown>[]> {
  const rows = await tryLoad(url);
  if (!rows) throw new Error(`Parquet not found: ${url}`);
  return rows;
}

/**
 * Load the sample points for the embedding view. Prefers the rich `points.parquet`
 * (x,y + consensus_label + top anchors); falls back to bare `umap2.parquet` (x,y)
 * when the anchor overlay was disabled.
 */
export async function loadPoints(base = './data'): Promise<PointRow[]> {
  const rows = (await tryLoad(`${base}/points.parquet`))
            ?? (await tryLoad(`${base}/umap2.parquet`));
  if (!rows) throw new Error(`No points.parquet or umap2.parquet under ${base}/`);
  return rows as PointRow[];
}

/** A tidy prelabels row: one ranked anchor (within a kind) for one sample. */
export interface PrelabelRow {
  sample_id: string;
  anchor_kind: string;   // 'tag' | 'flag' | 'category'
  rank: number;
  anchor_name: string;
  score: number;
  [k: string]: unknown;
}

/** Load the ranked anchor suggestions (top-k per kind per sample); [] if absent. */
export async function loadPrelabels(base = './data'): Promise<PrelabelRow[]> {
  const rows = await tryLoad(`${base}/prelabels.parquet`);
  return (rows ?? []) as PrelabelRow[];
}

/** An anchor marker placed in umap2 space (centroid of its supporting samples). */
export interface AnchorPointRow {
  anchor_id: string;
  anchor_kind: string;   // 'tag' | 'flag' | 'category'
  anchor_name: string;
  x: number;
  y: number;
  n_support?: number;
  [k: string]: unknown;
}

/** Load the anchor marker positions; [] if absent. */
export async function loadAnchorPoints(base = './data'): Promise<AnchorPointRow[]> {
  const rows = await tryLoad(`${base}/anchor_points.parquet`);
  return (rows ?? []) as AnchorPointRow[];
}
