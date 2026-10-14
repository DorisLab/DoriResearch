import { expect, it, vi } from 'vitest';
import { parseOverview, readRunOverview } from './runOverview';
import type { PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

const item = {
  reference: { kind: 'run', id: 'run', version: '2' },
  project_format: 'dorislab.etf-momentum.v1',
  files: ['run.json', 'request.json', 'result.json'].map((path) => ({
    path,
    bytes: 20,
    media_type: 'application/json',
  })),
} as PublicationSummary;
it('does not format unavailable metrics or infer dates and status from an arbitrary report', () => {
  expect(
    parseOverview(
      JSON.stringify({
        schema: 'dorislab.backtest.overview.v1',
        created_at: 'invalid',
        status: 'registered',
        metrics: [
          { metric_id: 'total_return', status: 'undefined', unit: 'ratio', value: 0 },
          { metric_id: 'max_drawdown', status: 'computed', unit: 'CNY', value: 1 },
        ],
      }),
    ),
  ).toEqual({
    start: undefined,
    end: undefined,
    created: undefined,
    status: undefined,
    totalReturn: undefined,
    maxDrawdown: undefined,
  });
  expect(() => parseOverview('{"schema":"other"}')).toThrow();
});
it('reads legacy frozen evidence with the original exact version, without rewriting it', async () => {
  const files: Record<string, unknown> = {
    'run.json': {
      schema: 'dorislab.backtest.run.v1',
      status: 'succeeded',
      created_at: '2025-03-01T12:00:00Z',
    },
    'request.json': { profile: item.project_format, start: '2025-01-01', end: '2025-02-28' },
    'result.json': {
      schema: 'dorislab.backtest.result.v1',
      metrics: [{ metric_id: 'total_return', status: 'computed', unit: 'ratio', value: 0.12 }],
    },
  };
  const read = vi.fn(async (_ref, path: string) => JSON.stringify(files[path]));
  const host = { readPublicationFile: read } as unknown as ResearchHost;
  expect(await readRunOverview(item, host)).toMatchObject({
    start: '2025-01-01',
    end: '2025-02-28',
    status: '已完成',
    totalReturn: 0.12,
  });
  expect(read).toHaveBeenCalledWith(item.reference, 'result.json');
  read.mockClear();
  expect(await readRunOverview({ ...item, project_format: 'unknown' }, host)).toEqual({});
  expect(read).not.toHaveBeenCalled();
});
