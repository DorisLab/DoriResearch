import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { ReadingRegion } from '../../ui/ReadingRegion';

function select(node: Node) {
  const range = document.createRange();
  range.selectNodeContents(node);
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  fireEvent(document, new Event('selectionchange'));
}

test('code select all excludes format notices and preserves the final source newline', () => {
  const view = render(
    <ReadingRegion>
      <p role="status">格式化不可用</p>
      <pre className="file-code">original{'\n'}</pre>
    </ReadingRegion>,
  );
  const root = view.container.querySelector('.reading-region')!;
  fireEvent.keyDown(root, { key: 'a', ctrlKey: true });
  const data = { setData: vi.fn() };
  fireEvent.copy(root, { clipboardData: data });
  expect(data.setData).toHaveBeenCalledWith('text/plain', 'original\n');
});

test('select all is scoped to one reader, preserves input editing and copies plain text', () => {
  const view = render(
    <>
      <aside>other pane</aside>
      <ReadingRegion>
        <pre>first{'\n'}second</pre>
        <input defaultValue="input" />
      </ReadingRegion>
    </>,
  );
  const root = view.container.querySelector('.reading-region')!;
  fireEvent.keyDown(root, { key: 'a', ctrlKey: true });
  expect(window.getSelection()?.toString()).toBe('first\nsecond');
  const data = { setData: vi.fn() };
  fireEvent.copy(root, { clipboardData: data });
  expect(data.setData).toHaveBeenCalledWith('text/plain', 'first\nsecond');
  select(view.container.querySelector('aside')!);
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'a', ctrlKey: true });
  expect(window.getSelection()?.toString()).toBe('other pane');
});

test('context menu snapshots selection, quotes it and keeps unselected actions disabled', async () => {
  const reference = vi.fn();
  const view = render(
    <ReadingRegion reference={reference}>
      <p>chosen text</p>
    </ReadingRegion>,
  );
  const root = view.container.querySelector('.reading-region')!;
  act(() => window.getSelection()?.removeAllRanges());
  fireEvent.contextMenu(root, { clientX: 20, clientY: 20 });
  expect(screen.getByRole('menuitem', { name: /复制/ })).toHaveAttribute('data-disabled');
  fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' });
  select(view.container.querySelector('p')!);
  fireEvent.contextMenu(root, { clientX: 20, clientY: 20 });
  fireEvent.click(screen.getByRole('menuitem', { name: '引用选中文字' }));
  await vi.waitFor(() =>
    expect(reference).toHaveBeenCalledWith(expect.objectContaining({ text: 'chosen text' })),
  );
});
