import type { Reference, Target } from '../types';
import type { ChartView } from './chartView';

export function chartReference(
  source: Target,
  block: string,
  rows: Record<string, unknown>[],
  view: ChartView,
): Reference {
  const row = rows[Math.min(view.index, rows.length - 1)] ?? {};
  const path = (JSON.parse(block) as { src?: string }).src ?? 'inline';
  const date = String(row.date ?? row['日期'] ?? '');
  return {
    schemaVersion: 1,
    source,
    kind: 'chart',
    locator: `chart:${path}`,
    quote: `${source.title} · ${path}${date ? ` · ${date}` : ''}`,
    createdAt: new Date().toISOString(),
    chart: {
      metric: path,
      runIds: source.kind === 'run' ? [source.id] : [],
      date,
      values: Object.fromEntries(
        Object.entries(row).filter(
          (entry): entry is [string, number] =>
            typeof entry[1] === 'number' && Number.isFinite(entry[1]),
        ),
      ),
      zoom: [...view.zoom],
      hidden: [...view.hidden],
    },
  };
}
