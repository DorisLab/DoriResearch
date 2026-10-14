import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { StrategyEntries, StudyEntries } from './StudioEntries';
import { StudioRuns } from './StudioRuns';
import type { PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

const study: PublicationSummary = {
  reference: { kind: 'study', id: 'study', version: '2' },
  title: '正式研究',
  summary: '简短结论',
  origin: 'project',
  data_nature: 'real',
  registered_at: 1,
  snippet: '',
  cover: null,
};
const strategy: PublicationSummary = {
  ...study,
  reference: { kind: 'strategy', id: 'strategy', version: '2' },
  title: '正式策略',
  references: [{ ...study.reference, version: '1' }],
};
const run: PublicationSummary = {
  ...study,
  reference: { kind: 'run', id: 'run', version: '1' },
  title: '正式运行',
  references: [strategy.reference],
  project_format: 'dorislab.etf-momentum.v1',
  files: [
    {
      path: 'overview.json',
      bytes: 100,
      media_type: 'application/json',
      role: 'data',
      sha256: 'a',
    },
  ],
};
const host: ResearchHost = { protocolVersion: 1, open: vi.fn(), reference: vi.fn() };

it('keeps studies compact, counts only exact strategy versions and opens historical sources exactly', async () => {
  const publications = [
    study,
    strategy,
    run,
    {
      ...run,
      reference: { ...run.reference, id: 'old-run' },
      references: [{ ...strategy.reference, version: '1' }],
    },
  ];
  render(
    <>
      <StudyEntries items={[study]} host={host} />
      <StrategyEntries items={[strategy]} publications={publications} host={host} />
    </>,
  );
  expect(screen.getByRole('heading', { name: '正式研究' })).toBeVisible();
  expect(screen.getByText('当前版本 · 1 次运行')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: '关联研究 · v1' }));
  expect(host.open).toHaveBeenLastCalledWith({
    ...study.reference,
    version: '1',
    title: '关联研究',
  });
});
it('keeps a failed metadata row openable, retries locally and replaces rows safely on version change', async () => {
  const read = vi
    .fn()
    .mockRejectedValueOnce(new Error('hash mismatch'))
    .mockResolvedValue(
      JSON.stringify({
        schema: 'dorislab.backtest.overview.v1',
        status: 'succeeded',
        start: '2025-01-01',
        end: '2025-02-28',
        metrics: [{ metric_id: 'total_return', status: 'computed', unit: 'ratio', value: 0.12 }],
      }),
    );
  const connected = { ...host, readPublicationFile: read };
  const view = render(<StudioRuns items={[run]} publications={[run, strategy]} host={connected} />);
  await screen.findByText(/运行信息暂不可用/);
  await userEvent.click(screen.getByRole('button', { name: '正式运行' }));
  expect(host.open).toHaveBeenLastCalledWith({ ...run.reference, title: run.title });
  await userEvent.click(screen.getByRole('button', { name: '重试' }));
  await screen.findByText('12.00%');
  expect(screen.getAllByRole('columnheader').map((el) => el.textContent)).toEqual([
    '运行',
    '策略版本',
    '数据区间',
    '运行状态 / 时间',
    '区间收益',
    '最大回撤',
  ]);
  view.rerender(
    <StudioRuns
      items={[{ ...run, reference: { ...run.reference } }]}
      publications={[run, strategy]}

      host={connected}
    />,
  );
  expect(read).toHaveBeenCalledTimes(2);
  const next = { ...run, reference: { ...run.reference, version: '2' }, project_format: 'unknown' };
  view.rerender(<StudioRuns items={[next]} publications={[next, strategy]} host={connected} />);
  await waitFor(() => expect(screen.queryByText('12.00%')).not.toBeInTheDocument());
  expect(screen.queryByText('已完成')).not.toBeInTheDocument();
});

it('opens row and keyboard targets while preserving text selection and nested actions', async () => {
  vi.mocked(host.open).mockClear();
  const view = render(<StudyEntries items={[study]} host={host} />);
  const row = view.container.querySelector('article')!;
  await userEvent.click(screen.getByText('简短结论'));
  expect(host.open).toHaveBeenCalledTimes(1);
  row.focus();
  await userEvent.keyboard('{Enter}');
  expect(host.open).toHaveBeenCalledTimes(2);
  const selection = vi
    .spyOn(window, 'getSelection')
    .mockReturnValue({ toString: () => '结论' } as Selection);
  await userEvent.click(screen.getByText('简短结论'));
  expect(host.open).toHaveBeenCalledTimes(2);
  selection.mockRestore();
  await userEvent.click(screen.getByRole('button', { name: '正式研究' }));
  expect(host.open).toHaveBeenCalledTimes(3);
  expect(screen.queryByText('真实数据')).not.toBeInTheDocument();
  expect(screen.queryByText('v2')).not.toBeInTheDocument();
});

it('keeps separators out of table navigation and preserves the second run target', async () => {
  const next = { ...run, reference: { ...run.reference, id: 'next' }, title: '第二次运行' };
  const view = render(<StudioRuns items={[run, next]} publications={[strategy]} host={host} />);
  expect(screen.getAllByRole('row')).toHaveLength(3);
  expect(screen.getAllByRole('rowheader')).toHaveLength(2);
  const divider = view.container.querySelector('.ui-divider')!;
  expect(divider.closest('tr')).toHaveAttribute('aria-hidden', 'true');
  expect(divider.closest('td')).toHaveAttribute('colspan', '6');
  await userEvent.click(screen.getByRole('button', { name: '第二次运行' }));
  expect(host.open).toHaveBeenLastCalledWith({ ...next.reference, title: next.title });
  view.rerender(<StudioRuns items={[next]} publications={[strategy]} host={host} />);
  expect(view.container.querySelector('.ui-divider')).toBeNull();
});

afterEach(cleanup);
