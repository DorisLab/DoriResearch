import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { ContentBlock } from './ContentBlock';
import { BacktestPanel } from './BacktestPanel';
import type { ResearchHost } from '../types';

vi.mock('echarts', () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}));
const reference = { kind: 'study' as const, id: 'study', version: '1' };
const host: ResearchHost = { protocolVersion: 1, open: vi.fn(), reference: vi.fn() };
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});

it('keeps a malformed metric local and reads inline metrics without a layout document', async () => {
  const view = render(
    <ContentBlock
      kind="metrics"
      value='[{"label":"收益","value":{"bad":1}}]'
      reference={reference}
      host={host}
    />,
  );
  expect(await screen.findByRole('alert')).toHaveTextContent('指标组');
  view.rerender(
    <ContentBlock
      kind="metrics"
      value='[{"label":"胜率","value":70,"unit":"%"}]'
      reference={reference}
      host={host}
    />,
  );
  expect(await screen.findByText('胜率')).toBeVisible();
  expect(await screen.findByText('70')).toBeVisible();
});

it('queries and sorts the full table before paging and resets the page on search', async () => {
  const request = vi.fn().mockImplementation(async (_operation, args) => ({
    columns: ['日期'],
    rows: [{ 日期: '2025-01-01' }],
    total: args.query ? 1 : 21,
    page: args.page,
  }));
  render(
    <ContentBlock
      kind="datatable"
      value='{"src":"trades.csv"}'
      reference={reference}
      host={{ ...host, request }}
    />,
  );
  await userEvent.click(await screen.findByRole('button', { name: '下一页' }));
  await waitFor(() =>
    expect(request).toHaveBeenLastCalledWith('table', expect.objectContaining({ page: 2 })),
  );
  await userEvent.type(screen.getByRole('textbox', { name: '筛选表格' }), '01');
  await waitFor(() =>
    expect(request).toHaveBeenLastCalledWith(
      'table',
      expect.objectContaining({ page: 1, query: '01' }),
    ),
  );
  await userEvent.click(screen.getByRole('button', { name: '日期' }));
  await waitFor(() =>
    expect(request).toHaveBeenLastCalledWith('table', expect.objectContaining({ sort: '日期' })),
  );
});

it('manual backtest passes temporary parameters and opens its independent saved result', async () => {
  const result = { kind: 'run', id: 'result', version: '1' };
  const request = vi.fn().mockResolvedValue({ id: 'job', status: 'succeeded', result });
  render(
    <BacktestPanel
      reference={{ ...reference, kind: 'strategy' }}
      host={{ ...host, request }}
      config={{
        callable: 'example:run',
        date_range: { start: '2025-01-01', end: '2025-12-31' },
        parameters: [{ name: 'cost', label: '费用', type: 'number', default: 10 }],
      }}
    />,
  );
  await userEvent.click(screen.getByText('回测这套策略'));
  await userEvent.clear(screen.getByLabelText('费用'));
  await userEvent.type(screen.getByLabelText('费用'), '20');
  await userEvent.click(screen.getByRole('button', { name: '开始回测' }));
  expect(request).toHaveBeenCalledWith(
    'backtest',
    expect.objectContaining({ parameters: { cost: 20 }, start: '2025-01-01', end: '2025-12-31' }),
  );
  await waitFor(() => expect(host.open).toHaveBeenCalledWith({ ...result, title: '策略回测结果' }));
  expect(host.open).toHaveBeenCalledTimes(1);
});
