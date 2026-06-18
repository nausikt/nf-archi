/**
 * Shared point-interaction helpers for the Cosmograph views.
 *
 * Keeps the "hover shows the question title, click opens the source URL" behaviour
 * in one place so every embedding view (explore / clustering / sampled) wires it
 * the same way without duplicating the truncation / navigation logic.
 */
import type { CosmographConfig } from '@cosmograph/cosmograph';

const MAX = 90;

/** Label accessor: first line of the question, truncated — the "title". */
export function pointTitle(value: unknown): string {
  const s = String(value ?? '').split('\n')[0].trim();
  return s.length > MAX ? `${s.slice(0, MAX)}…` : s;
}

/** onPointClick handler: open the sample's external_url (by point index) in a new tab. */
export function openUrlOnClick(urlByIndex: Map<number, string>): CosmographConfig['onPointClick'] {
  return (index: number) => {
    const url = urlByIndex.get(Number(index));
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  };
}

/**
 * Deep link into the Argilla review queue for a single record. Argilla has no
 * per-record permalink, but the annotation page accepts a `metadata` filter, and
 * every exported record carries a `sample_id` terms-metadata property.
 *
 * Frontend URL format (from argilla RecordCriteria): `metadata=<name>.<value>`,
 * multiple filters joined by `~`, values split on `.`. `sample_id` is a 12-char
 * SHA-256 hex (no `.`/`~`), so this is an exact, collision-free deep link.
 */
export function argillaRecordUrl(annotationUrl: string | undefined, sampleId: string | undefined): string | undefined {
  if (!annotationUrl || !sampleId) return undefined;
  return `${annotationUrl}?metadata=sample_id.${encodeURIComponent(sampleId)}`;
}
