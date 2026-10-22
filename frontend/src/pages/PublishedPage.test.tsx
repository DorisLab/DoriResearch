import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { PublicationContent } from '../publicationContracts';
import { PublishedPage } from './PublishedPage';

afterEach(cleanup);
test('related navigation uses full names and current identities; collapsed items expand', async () => {
  const host = { protocolVersion: 1 as const, open: vi.fn(), reference: vi.fn() };
  const related = Array.from({ length: 5 }, (_, i) => ({
    reference: { kind: 'strategy' as const, id: `strategy-${i}`, version: '2' },
    title: `上证50ETF固定底仓与网格策略完整名称 ${i}`,
  }));
  render(<PublishedPage content={{ ...content, related }} host={host} />);
  fireEvent.click(screen.getByRole('button', { name: `策略：${related[0].title}` }));
  expect(host.open).toHaveBeenCalledWith({ ...related[0].reference, title: related[0].title });
  expect(screen.queryByText(/· v/)).not.toBeInTheDocument();
  expect(screen.queryByText(related[4].title)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '展开其余 2 项' }));
  expect(screen.getByText(related[4].title)).toBeVisible();
});

test('encoded attachment links and exact inline filenames open only existing files', () => {
  const previewFile = vi.fn();
  const host = { protocolVersion: 1 as const, open: vi.fn(), reference: vi.fn(), previewFile };
  const path = '策略/[底仓] 网格#1%.py';
  render(
    <PublishedPage
      content={{
        ...content,
        files: [{ ...content.files[0], path }],
        body: `[代码](<${encodeURIComponent(path)}>)\n\n下载本页附件 \`${path}\`。\n\n\`missing.py\`\n\n\`\`\`\n${path}\n\`\`\``,
      }}
      host={host}
    />,
  );
  fireEvent.click(screen.getByRole('button', { name: '代码' }));
  fireEvent.click(screen.getByRole('button', { name: path }));
  expect(previewFile.mock.calls).toEqual([[path], [path]]);
  expect(screen.queryByRole('button', { name: 'missing.py' })).not.toBeInTheDocument();
});
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
