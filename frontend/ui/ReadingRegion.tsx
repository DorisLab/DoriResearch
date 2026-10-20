import { useRef, type ReactNode } from 'react';
import * as Menu from '@radix-ui/react-context-menu';
import { ChatCircleDots as MessageCirclePlus } from '@phosphor-icons/react';
import { editingTarget, readSelection, type ReadingSelection } from './readingSelection';
import { useReadingRegion } from './useReadingRegion';
import './reading-region.css';

export function ReadingRegion({
  children,
  reference,
  canReference = () => true,
}: {
  children: ReactNode;
  reference?: (value: ReadingSelection) => void | Promise<void>;
  canReference?: (value: ReadingSelection) => boolean;
}) {
  const { root, selected, position, error, open, restore, all, copy, quote, hide } =
    useReadingRegion(reference);
  const quotable = !!selected?.text.trim() && !!reference && canReference(selected);
  return (
    <>
      <Menu.Root modal={false} onOpenChange={open}>
        <Menu.Trigger asChild>
          <div
            ref={root}
            className="reading-region"
            tabIndex={0}
            onBlur={hide}
            onMouseDown={(event) => {
              if (!editingTarget(event.target) && !(event.target as Element).closest('button, a'))
                root.current?.focus({ preventScroll: true });
            }}
            onContextMenu={(event) => {
              if (editingTarget(event.target)) event.preventDefault();
            }}
            onCopy={(event) => {
              if (editingTarget(event.target)) return;
              const value = readSelection(root.current);
              if (value) {
                event.clipboardData.setData('text/plain', value.text);
                event.preventDefault();
              }
            }}
            onKeyDown={(event) => {
              if (editingTarget(event.target) || event.isDefaultPrevented()) return;
              if (
                event.ctrlKey &&
                !event.altKey &&
                !event.shiftKey &&
                event.key.toLowerCase() === 'a'
              ) {
                event.preventDefault();
                event.stopPropagation();
                all();
              }
              if (event.key === 'Escape') hide();
            }}
          >
            {children}
          </div>
        </Menu.Trigger>
        <ReadingMenu
          selected={!!selected}
          quotable={quotable}
          copy={copy}
          all={all}
          quote={quote}
          restore={restore}
        />
      </Menu.Root>
      {quotable && position && (
        <button
          className="reading-selection-action"
          style={{ left: position.x, top: position.y }}
          onMouseDown={(event) => event.preventDefault()}
          onClick={quote}
        >
          <MessageCirclePlus aria-hidden="true" />
          引用选中文字
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </>
  );
}

function ReadingMenu({
  selected,
  quotable,
  copy,
  all,
  quote,
  restore,
}: {
  selected: boolean;
  quotable: boolean;
  copy(): void;
  all(): void;
  quote(): void;
  restore(): void;
}) {
  const outside = useRef(false);
  return (
    <Menu.Portal>
      <Menu.Content
        className="reading-menu"
        collisionPadding={8}
        onInteractOutside={() => {
          outside.current = true;
        }}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          if (!outside.current) restore();
          outside.current = false;
        }}
      >
        <Menu.Item disabled={!selected} onSelect={copy}>
          复制 <kbd>Ctrl+C</kbd>
        </Menu.Item>
        <Menu.Item onSelect={all}>
          全选 <kbd>Ctrl+A</kbd>
        </Menu.Item>
        <Menu.Separator />
        <Menu.Item disabled={!quotable} onSelect={quote}>
          引用选中文字
        </Menu.Item>
      </Menu.Content>
    </Menu.Portal>
  );
}
