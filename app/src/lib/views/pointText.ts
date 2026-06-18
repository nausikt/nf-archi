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
 * Deep link into the Argilla review queue for a record. Argilla has no per-record
 * permalink, so we open the dataset's annotation page with the record's question
 * pre-filled in the search bar (`query`) — it lands on / filters to that item.
 */
export function argillaRecordUrl(annotationUrl: string | undefined, question: string | undefined): string | undefined {
  if (!annotationUrl || !question) return undefined;
  const q = question.split('\n')[0].trim();
  if (!q) return undefined;
  return `${annotationUrl}?query=${encodeURIComponent(q)}`;
}
