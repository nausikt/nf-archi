/**
 * Tolerant Nextflow mermaid-DAG parser (pure, framework-free).
 *
 * Nextflow's `-with-dag *.mmd` emits a `flowchart TB` of nested `subgraph`s:
 *   - processes are stadium nodes   `vN(["Embed"])`
 *   - named channels/values are     `vN["ch_embeddings"]`
 *   - anonymous operator junctions  `vN(( ))`
 *   - edges are                      `vA --> vB`  (optionally `-->|label|`)
 *
 * We flatten the subgraph tree (keeping the nearest named subgraph as `group`)
 * into a plain id/label/kind graph. The parser is line-based and shape-tolerant
 * so it survives mermaid dialect drift across Nextflow versions.
 */

export type DagKind = 'process' | 'io' | 'junction' | 'operator';

export interface DagNode {
  id: string;
  label: string;
  kind: DagKind;
  group?: string;
}

export interface DagEdge {
  source: string;
  target: string;
  label?: string;
}

export interface DagGraph {
  nodes: DagNode[];
  edges: DagEdge[];
}

// Shape body (the text after the leading id) -> kind + inner label. Most
// specific brackets first so e.g. `([x])` is not mis-read as `(x)`.
const SHAPES: ReadonlyArray<{ re: RegExp; kind: DagKind }> = [
  { re: /^\(\[(.*)\]\)$/, kind: 'process'  },   // ([label])  stadium    -> process
  { re: /^\[\[(.*)\]\]$/, kind: 'process'  },   // [[label]]  subroutine -> process
  { re: /^\(\((.*)\)\)$/, kind: 'junction' },   // ((label))  circle     -> operator junction
  { re: /^\{\{(.*)\}\}$/, kind: 'operator' },   // {{label}}
  { re: /^\[(.*)\]$/,     kind: 'io'       },   // [label]    channel / value
  { re: /^\((.*)\)$/,     kind: 'operator' },   // (label)
  { re: /^\{(.*)\}$/,     kind: 'operator' },   // {label}
];

const ID = /^[A-Za-z0-9_]+/;
const ARROW = /(-{2,3}>|-\.->|={2,3}>|x--x|o--o|-{2,3}|-\.-|={2,3})/;

const unquote = (s: string) => s.replace(/^["']|["']$/g, '').trim();

/** Parse an `id<shape>` token (e.g. `v7(["Embed"])`) into a node, or null. */
function parseToken(token: string): DagNode | null {
  const t = token.trim();
  const idm = t.match(ID);
  if (!idm) return null;
  const id = idm[0];
  const body = t.slice(id.length).trim();
  if (!body) return { id, label: '', kind: 'junction' };   // bare endpoint: enrich later
  for (const { re, kind } of SHAPES) {
    const m = body.match(re);
    if (m) return { id, label: unquote(m[1] ?? ''), kind };
  }
  return { id, label: '', kind: 'junction' };
}

/** Derive a readable group name from a `subgraph` header line. */
function subgraphTitle(line: string): string | undefined {
  const m = line.match(/^subgraph\s+(?:"([^"]*)"|'([^']*)'|(\S+))/);
  const raw = (m?.[1] ?? m?.[2] ?? m?.[3] ?? '').trim();
  if (!raw) return undefined;                                 // `subgraph " "`
  const bracket = raw.match(/\[([^\]]+)\]\s*$/);              // `Foo:Bar [Bar]` -> Bar
  if (bracket) return bracket[1].trim();
  const seg = raw.split(':').pop()!.trim();                   // `Foo:Bar` -> Bar
  return seg || undefined;
}

export function parseMermaid(text: string): DagGraph {
  const nodes = new Map<string, DagNode>();
  const edges: DagEdge[] = [];
  const stack: (string | undefined)[] = [];

  const currentGroup = (): string | undefined => {
    for (let i = stack.length - 1; i >= 0; i--) if (stack[i]) return stack[i];
    return undefined;
  };

  // A shaped declaration wins over a bare edge-endpoint mention.
  const upsert = (n: DagNode | null, group?: string) => {
    if (!n) return;
    const prev = nodes.get(n.id);
    if (!prev) { nodes.set(n.id, { ...n, group }); return; }
    if (n.label) prev.label = n.label;
    if (n.kind !== 'junction') prev.kind = n.kind;
    if (group && !prev.group) prev.group = group;
  };

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (/^(flowchart|graph|direction|classDef|class|style|linkStyle)\b/.test(line)) continue;
    if (line.startsWith('%%')) continue;

    if (/^subgraph\b/.test(line)) { stack.push(subgraphTitle(line)); continue; }
    if (line === 'end') { stack.pop(); continue; }

    const arrow = line.match(ARROW);
    if (arrow && arrow.index !== undefined) {
      const lhs = line.slice(0, arrow.index);
      let rhs = line.slice(arrow.index + arrow[0].length);
      let label: string | undefined;
      const lm = rhs.match(/^\s*\|([^|]*)\|\s*/);              // `-->|name| vB`
      if (lm) { label = lm[1].trim(); rhs = rhs.slice(lm[0].length); }
      const a = parseToken(lhs);
      const b = parseToken(rhs);
      const g = currentGroup();
      upsert(a, g);
      upsert(b, g);
      if (a && b) edges.push({ source: a.id, target: b.id, label });
      continue;
    }

    upsert(parseToken(line), currentGroup());
  }

  return { nodes: [...nodes.values()], edges };
}
