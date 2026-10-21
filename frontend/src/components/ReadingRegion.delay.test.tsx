import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { ReadingRegion } from '../../ui/ReadingRegion';

afterEach(() => vi.useRealTimers());

test('selection waits for release and a quiet interval; cancellation never resurfaces the action', () => {
  vi.useFakeTimers();
  const descriptor = Object.getOwnPropertyDescriptor(Range.prototype, 'getClientRects');
  Object.defineProperty(Range.prototype, 'getClientRects', {
    configurable: true,
    value: () => [{ left: 20, top: 80, bottom: 100 }],
  });
  const view = render(
    <ReadingRegion reference={vi.fn()}>
      <p>selected text</p>
    </ReadingRegion>,
  );
  const root = view.container.querySelector<HTMLElement>('.reading-region')!;
  const select = (start = 0) => {
    const range = document.createRange();
    range.selectNodeContents(root.querySelector('p')!);
    range.setStart(root.querySelector('p')!.firstChild!, start);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    fireEvent(document, new Event('selectionchange'));
  };
  const advance = (ms: number) => act(() => vi.advanceTimersByTime(ms));
  const action = () => screen.queryByRole('button', { name: '引用选中文字' });
  try {
    root.focus();
    fireEvent.pointerDown(root, { button: 0 });
    select();
    advance(600);
    expect(action()).toBeNull();
    fireEvent.pointerUp(root);
    advance(250);
    expect(action()).toBeNull();
    advance(50);
    expect(action()).not.toBeNull();
    fireEvent.keyDown(root, { key: 'a', ctrlKey: true });
    advance(300);
    fireEvent.keyDown(root, { key: 'Escape' });
    fireEvent(document, new Event('selectionchange'));
    advance(400);
    expect(action()).toBeNull();
    fireEvent.keyDown(root, { key: 'a', ctrlKey: true });
    advance(250);
    expect(action()).toBeNull();
    advance(50);
    expect(action()).not.toBeNull();
    select(1);
    expect(action()).toBeNull();
    fireEvent.keyDown(root, { key: 'Escape' });
    advance(400);
    expect(action()).toBeNull();
    select(2);
    fireEvent.blur(root);
    advance(400);
    expect(action()).toBeNull();
  } finally {
    view.unmount();
    if (descriptor) Object.defineProperty(Range.prototype, 'getClientRects', descriptor);
    else Reflect.deleteProperty(Range.prototype, 'getClientRects');
  }
});
