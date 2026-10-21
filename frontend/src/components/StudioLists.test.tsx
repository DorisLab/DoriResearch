import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { StrategyEntries, StudyEntries } from './StudioEntries';
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

afterEach(cleanup);
