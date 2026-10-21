import { readSelection, type ReadingSelection } from './readingSelection';

export function observeReadingSelection(
  root: HTMLElement,
  menuOpen: () => boolean,
  selected: (value: ReadingSelection | null) => void,
  place: (value: ReadingSelection | null) => void,
) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let dragging = false;
  let previous: ReadingSelection | null = null;
  const hide = () => {
    clearTimeout(timer);
    place(null);
  };
  const update = () => {
    if (menuOpen()) return;
    const value = readSelection(root);
    if (sameSelection(value, previous)) return;
    previous = value;
    hide();
    selected(value);
    if (value && !dragging && root.contains(root.ownerDocument.activeElement)) {
      timer = setTimeout(() => place(readSelection(root)), 300);
    }
  };
  const down = (event: PointerEvent) => {
    if ((event.target as Element)?.closest('.reading-selection-action, .reading-menu')) return;
    dragging = event.button === 0;
    previous = null;
    hide();
  };
  const up = () => {
    if (!dragging) return;
    dragging = false;
    previous = null;
    update();
  };
  const cancel = () => {
    dragging = false;
    hide();
  };
  const document = root.ownerDocument;
  const window = document.defaultView!;
  document.addEventListener('selectionchange', update);
  document.addEventListener('pointerdown', down);
  document.addEventListener('pointerup', up);
  document.addEventListener('pointercancel', cancel);
  window.addEventListener('scroll', hide, true);
  window.addEventListener('resize', hide);
  return {
    hide,
    refresh: () => {
      previous = null;
      update();
    },
    dispose: () => {
      hide();
      document.removeEventListener('selectionchange', update);
      document.removeEventListener('pointerdown', down);
      document.removeEventListener('pointerup', up);
      document.removeEventListener('pointercancel', cancel);
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
    },
  };
}

function sameSelection(a: ReadingSelection | null, b: ReadingSelection | null) {
  return (
    a === b ||
    (!!a &&
      !!b &&
      a.text === b.text &&
      a.range.startContainer === b.range.startContainer &&
      a.range.startOffset === b.range.startOffset &&
      a.range.endContainer === b.range.endContainer &&
      a.range.endOffset === b.range.endOffset)
  );
}
