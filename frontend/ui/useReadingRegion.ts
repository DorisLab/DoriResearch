import { useEffect, useRef, useState } from 'react';
import { observeReadingSelection } from './observeReadingSelection';
import {
  copyReading,
  readSelection,
  restoreSelection,
  selectReading,
  type ReadingSelection,
} from './readingSelection';

export function useReadingRegion(reference?: (value: ReadingSelection) => void | Promise<void>) {
  const root = useRef<HTMLDivElement>(null);
  const saved = useRef<ReadingSelection | null>(null);
  const menuOpen = useRef(false);
  const [selected, setSelected] = useState<ReadingSelection | null>(null);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const [error, setError] = useState('');
  const dismiss = useRef(() => setPosition(null));
  useEffect(() => {
    if (!root.current) return;
    const observer = observeReadingSelection(
      root.current,
      () => menuOpen.current,
      (value) => {
        saved.current = value;
        setSelected(value);
      },
      (value) => setPosition(selectionPosition(value)),
    );
    dismiss.current = observer.hide;
    return observer.dispose;
  }, []);
  return {
    root,
    selected,
    position,
    error,
    hide: () => dismiss.current(),
    open: (open: boolean) => {
      menuOpen.current = open;
      if (open) {
        saved.current = readSelection(root.current);
        setSelected(saved.current);
        dismiss.current();
      }
    },
    restore: () => {
      if (root.current) restoreSelection(root.current, saved.current);
    },
    all: () => {
      if (root.current) saved.current = selectReading(root.current);
      setSelected(saved.current);
    },
    copy: () => {
      if (root.current && saved.current)
        void copyReading(root.current, saved.current).catch((cause) =>
          setError(`复制失败：${String(cause)}`),
        );
    },
    quote: () => {
      const value = saved.current;
      if (value && reference)
        void Promise.resolve()
          .then(() => reference(value))
          .catch((cause) => setError(String(cause)));
      dismiss.current();
    },
  };
}

function selectionPosition(value: ReadingSelection | null) {
  const rect = value?.range.getClientRects?.()[0];
  return rect
    ? {
        x: Math.max(8, Math.min(rect.left, window.innerWidth - 180)),
        y: Math.max(
          8,
          Math.min(rect.top > 48 ? rect.top - 40 : rect.bottom + 8, window.innerHeight - 48),
        ),
      }
    : null;
}
