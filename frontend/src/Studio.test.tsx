import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Studio } from './Studio';
import type { PublicationSummary } from './publicationContracts';
import type { PublicationPage, ResearchHost } from './types';

const item: PublicationSummary = {
  reference: { kind: 'study', id: 'study', version: '1' },
  title: '正式研究',
  summary: '可选择的摘要',
  origin: 'project',
  data_nature: 'real',
  registered_at: 1,
  snippet: '',
  cover: null,
};
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

it('queries the host before paging, remembers each category and keeps page when records update', async () => {
  const query = vi.fn(async (request) => ({
    items: [{ ...item, title: `成果第${request.page}页` }],
    total: 25,
    page: request.page,
  }));
  const host: ResearchHost = {
    protocolVersion: 1,
    open: vi.fn(),
    reference: vi.fn(),
    queryPublications: query,
  };
  const view = render(<Studio host={host} />);
  await screen.findByText('第 1–20 项，共 25 项');
  await userEvent.click(screen.getByText('下一页'));
  await screen.findByText('第 21–25 项，共 25 项');
  await userEvent.click(screen.getByRole('button', { name: '策略' }));
  await screen.findByText('第 1–20 项，共 25 项');
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: '规则' } });
  await waitFor(() =>
    expect(query).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: 'strategy', query: '规则', page: 1 }),
    ),
  );
  await userEvent.click(screen.getByRole('button', { name: '研究' }));
  await screen.findByText('第 21–25 项，共 25 项');
  view.rerender(<Studio host={host} publications={[item]} />);
  await waitFor(() =>
    expect(query).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: 'study', query: '', page: 2 }),
    ),
  );
  view.unmount();
  render(<Studio host={host} />);
  await screen.findByText('第 21–25 项，共 25 项');
});

it('ignores late query results and can recover from a failed search', async () => {
  let old: (page: PublicationPage) => void = () => {};
  const query = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          old = resolve;
        }),
    )
    .mockRejectedValueOnce(new Error('read failed'))
    .mockResolvedValue({ items: [item], total: 1, page: 1 });
  const host: ResearchHost = {
    protocolVersion: 1,
    open: vi.fn(),
    reference: vi.fn(),
    queryPublications: query,
  };
  render(<Studio host={host} />);
  await waitFor(() => expect(query).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: '新查询' } });
  await screen.findByRole('alert');
  old({ items: [{ ...item, title: '迟到结果' }], total: 1, page: 1 });
  await userEvent.click(screen.getByRole('button', { name: '重试' }));
  await screen.findByRole('heading', { name: item.title });
  expect(screen.queryByText('迟到结果')).not.toBeInTheDocument();
  expect(screen.queryByRole('navigation', { name: '成果分页' })).not.toBeInTheDocument();
});

afterEach(cleanup);

it('recovers from a removed series and remembers the clamped page after records disappear', async () => {
  const saved = { query: '', series: 'removed-series', sort: 'newest', page: 3, scroll: 0 };
  localStorage.setItem(
    'dorislab.research.studio.v2',
    JSON.stringify({
      section: 'study',
      views: { study: saved, strategy: saved, run: saved },
    }),
  );
  const query = vi.fn(async () => ({ items: [item], total: 1, page: 1 }));
  const host: ResearchHost = {
    protocolVersion: 1,
    open: vi.fn(),
    reference: vi.fn(),
    queryPublications: query,
  };
  render(<Studio host={host} publications={[item]} />);
  await screen.findByRole('heading', { name: item.title });
  await waitFor(() =>
    expect(query).toHaveBeenLastCalledWith(expect.objectContaining({ series: '', page: 1 })),
  );
  expect(JSON.parse(localStorage.getItem('dorislab.research.studio.v2')!).views.study.page).toBe(1);
});
