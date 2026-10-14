import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { ChatCircleDots } from '@phosphor-icons/react';
import type { ResearchHost, Target } from '../types';

interface SelectedText {
  text: string;
  section: string;
  anchor: DOMRect;
}

export function TextSelection({
  source,
  host,
  children,
}: {
  source: Target;
  host: ResearchHost;
  children: ReactNode;
}) {
  const [selection, setSelection] = useState<SelectedText | null>(null);
  const action = useSelectionPosition(selection?.anchor);
  useEffect(() => {
    const clear = () => setSelection(null);
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') clear();
    };
    window.addEventListener('scroll', clear, true);
    window.addEventListener('keydown', escape);
    window.addEventListener('resize', clear);
    return () => {
      window.removeEventListener('scroll', clear, true);
      window.removeEventListener('keydown', escape);
      window.removeEventListener('resize', clear);
    };
  }, []);
  function capture() {
    const selected = window.getSelection();
    if (!selected || selected.isCollapsed || !selected.rangeCount) {
      setSelection(null);
      return;
    }
    const node = selected.anchorNode?.parentElement;
    if (!node?.closest('[data-research-text]')) return;
    // A multiline range's union starts at the left edge of later lines, not at
    // the first selected character. Use its first visible text fragment instead.
    const anchor = Array.from(selected.getRangeAt(0).getClientRects()).find(
      (rect) =>
        rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < window.innerHeight,
    );
    if (!anchor) return;
    setSelection({
      text: selected.toString(),
      section: node.closest('section')?.id ?? 'body',
      anchor,
    });
  }
  function attach() {
    if (!selection) return;
    host.reference({
      schemaVersion: 1,
      source,
      kind: 'text',
      locator: selection.section,
      quote: selection.text,
      createdAt: new Date().toISOString(),
    });
    setSelection(null);
  }
  return (
    <div
      data-research-text
      onMouseUp={capture}
      onKeyUp={capture}
      onScrollCapture={() => setSelection(null)}
    >
      {children}
      {selection && (
        <button
          ref={action}
          className="selection-action"
          onMouseDown={(event) => event.preventDefault()}
          onClick={attach}
        >
          <ChatCircleDots />
          引用选中文字
        </button>
      )}
    </div>
  );
}

function useSelectionPosition(anchor: DOMRect | undefined) {
  const action = useRef<HTMLButtonElement>(null);
  useLayoutEffect(() => {
    const button = action.current;
    if (!anchor || !button) return;
    const position = () => {
      const { width, height } = button.getBoundingClientRect();
      const { left, top, bottom } = anchor;
      const y = top - height - 8;
      button.style.left = `${Math.max(8, Math.min(left, window.innerWidth - width - 8))}px`;
      button.style.top = `${Math.max(8, Math.min(y >= 8 ? y : bottom + 8, window.innerHeight - height - 8))}px`;
    };
    position();
    const observer = new ResizeObserver(position);
    observer.observe(button);
    return () => observer.disconnect();
  }, [anchor]);
  return action;
}
