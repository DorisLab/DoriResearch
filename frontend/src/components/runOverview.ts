import type { PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

export type RunMetadataSource = Pick<PublicationSummary, 'reference' | 'project_format' | 'files'>;

export interface RunOverview {
  start?: string;
  end?: string;
  created?: string;
  status?: string;
  totalReturn?: number;
  maxDrawdown?: number;
}
function object(text: string): Record<string, unknown> {
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Invalid overview');
  return value as Record<string, unknown>;
}
function date(value: unknown) {
  return typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(value) &&
    Number.isFinite(Date.parse(value))
    ? value
    : undefined;
}
function metric(metrics: unknown, id: string) {
  if (!Array.isArray(metrics)) return;
  const found = metrics.find(
    (m: unknown) => m && typeof m === 'object' && 'metric_id' in m && m.metric_id === id,
  );
  return found?.status === 'computed' &&
    found.unit === 'ratio' &&
    typeof found.value === 'number' &&
    Number.isFinite(found.value)
    ? found.value
    : undefined;
}
function runStatus(value: unknown) {
  switch (value) {
    case 'succeeded':
      return '已完成';
    case 'failed':
      return '失败';
    case 'running':
      return '运行中';
    default:
      return undefined;
  }
}
export function parseOverview(text: string): RunOverview {
  const value = object(text);
  if (value.schema !== 'dorislab.backtest.overview.v1') throw new Error('Unsupported overview');
  return {
    start: date(value.start),
    end: date(value.end),
    created: date(value.created_at),
    status: runStatus(value.status),
    totalReturn: metric(value.metrics, 'total_return'),
    maxDrawdown: metric(value.metrics, 'max_drawdown'),
  };
}
export async function readRunOverview(
  item: RunMetadataSource,
  host: ResearchHost,
): Promise<RunOverview> {
  if (item.project_format !== 'dorislab.etf-momentum.v1' || !host.readPublicationFile) return {};
  const read = async (path: string) => {
    const file = item.files?.find(
      (file) =>
        file.path === path &&
        file.media_type === 'application/json' &&
        file.bytes <= 2 * 1024 * 1024,
    );
    return file ? host.readPublicationFile!(item.reference, path) : undefined;
  };
  const overview = await read('overview.json');
  if (overview) return parseOverview(overview);
  // Older frozen bundles remain readable without rewriting their files.
  const run = await read('run.json');
  const request = await read('request.json');
  const result = await read('result.json');
  return legacyOverview(run, request, result);
}
function legacyOverview(run?: string, request?: string, result?: string): RunOverview {
  const state = run ? object(run) : {};
  const input = request ? object(request) : {};
  const output = result ? object(result) : {};
  if (state.schema !== 'dorislab.backtest.run.v1') return {};
  return parseOverview(
    JSON.stringify({
      schema: 'dorislab.backtest.overview.v1',
      status: state.status,
      created_at: state.created_at,
      start: input.profile === 'dorislab.etf-momentum.v1' ? input.start : undefined,
      end: input.profile === 'dorislab.etf-momentum.v1' ? input.end : undefined,
      metrics: output.schema === 'dorislab.backtest.result.v1' ? output.metrics : undefined,
    }),
  );
}
