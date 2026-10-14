import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { PublicationContent } from '../publicationContracts';
import { PublishedPage } from './PublishedPage';

afterEach(cleanup);
test('files are collapsed and preview the selected path without inserting a duplicate cover', async () => {
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
  const previewFile = vi.fn();
  const host = { protocolVersion: 1 as const, open: vi.fn(), reference: vi.fn(), previewFile };
  const files = Array.from({ length: 24 }, (_, i) => ({
    ...content.files[0],
    path: `evidence-${i}.json`,
  }));
  const { container } = render(
    <PublishedPage
      content={{ ...content, body: '结论', files, cover_url: 'data:image/png;base64,AA==' }}
      host={host}
    />,
  );
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'evidence-0.json' })).not.toBeInTheDocument();
  const details = container.querySelector('details')!;
  details.open = true;
  fireEvent(details, new Event('toggle'));
  fireEvent.click(await screen.findByRole('button', { name: 'evidence-23.json' }));
  expect(previewFile).toHaveBeenCalledExactlyOnceWith('evidence-23.json');
  vi.unstubAllGlobals();
});
const content: PublicationContent = {
  item: {
    reference: { kind: 'study', id: 'one', version: '1' },
    title: '研究',
    summary: '摘要',
    snippet: '',
    origin: 'project',
    data_nature: 'synthetic',
    registered_at: 0,
  },
  body: '![曲线](chart.png)\n\n| A | B |\n| --- | --- |\n| 1 | 2 |',
  files: [{ path: 'chart.png', media_type: 'image/png', role: 'figure', bytes: 1, sha256: '' }],
  references: [],
  revision_note: '',
};

test.each(['png', 'svg+xml'])(
  'host rerenders preserve %s images and table contents',
  async (format) => {
    const host = {
      protocolVersion: 1 as const,
      open: vi.fn(),
      reference: vi.fn(),
      readImage: vi.fn(async () => `data:image/${format};base64,AA==`),
    };
    const { rerender } = render(<PublishedPage content={content} host={host} />);
    const image = await screen.findByRole('img', { name: '曲线' });
    for (let i = 0; i < 10; i++)
      rerender(<PublishedPage content={{ ...content, files: [...content.files] }} host={host} />);
    expect(screen.getByRole('img', { name: '曲线' })).toBe(image);
    expect(host.readImage).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('region', { name: '研究数据表' })).toContainElement(
      screen.getByRole('table'),
    );
    expect(screen.getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['1', '2']);
    rerender(
      <PublishedPage
        content={{
          ...content,
          item: { ...content.item, reference: { ...content.item.reference, version: '2' } },
        }}
        host={host}
      />,
    );
    expect(await screen.findByRole('img', { name: '曲线' })).not.toBe(image);
    expect(host.readImage).toHaveBeenCalledTimes(2);
  },
);
