import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { StudyEntries } from './StudioEntries';
import type { PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

it('shows a registered cover and lets a failed cover retry without hiding the publication', async () => {
  const item = {
    reference: { kind: 'study', id: 'one', version: '1' },
    title: 'Beta 研究',
    summary: '发现',
    data_nature: 'real',
    origin: 'project',
    registered_at: 1,
    cover: 'cover.png',
  } as PublicationSummary;
  const readCover = vi
    .fn()
    .mockRejectedValueOnce(new Error('missing'))
    .mockResolvedValue('data:image/png;base64,eA==');
  const host: ResearchHost = { protocolVersion: 1, open: vi.fn(), reference: vi.fn(), readCover };
  render(<StudyEntries items={[item]} host={host} />);
  await screen.findByText('封面暂不可用');
  expect(screen.getByRole('button', { name: 'Beta 研究' })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: '重试' }));
  await waitFor(() =>
    expect(screen.getByRole('img', { name: 'Beta 研究配图' })).toHaveAttribute(
      'src',
      'data:image/png;base64,eA==',
    ),
  );
  expect(readCover).toHaveBeenLastCalledWith(item.reference, 'cover.png');
  await userEvent.click(screen.getByRole('button', { name: '查看Beta 研究配图' }));
  expect(screen.getByRole('dialog')).toBeVisible();
  expect(host.open).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button', { name: '关闭' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
