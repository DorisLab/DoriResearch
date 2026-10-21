import * as Primitive from '@radix-ui/react-tooltip';
import { useEffect, useState, type ReactElement, type ReactNode } from 'react';
import './tooltip.css';

export function Tooltip({ children, content }: { children: ReactElement; content: ReactNode }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const leave = () => {
      if (!document.activeElement?.matches(':focus-visible')) close();
    };
    const hide = () => {
      if (document.hidden) close();
    };
    window.addEventListener('blur', close);
    document.addEventListener('visibilitychange', hide);
    document.documentElement.addEventListener('pointerleave', leave);
    return () => {
      window.removeEventListener('blur', close);
      document.removeEventListener('visibilitychange', hide);
      document.documentElement.removeEventListener('pointerleave', leave);
    };
  }, [open]);
  return (
    <Primitive.Provider delayDuration={350} skipDelayDuration={0}>
      <Primitive.Root open={open} onOpenChange={setOpen}>
        <Primitive.Trigger asChild>{children}</Primitive.Trigger>
        <Primitive.Portal>
          <Primitive.Content
            className="research-tooltip"
            side="top"
            sideOffset={8}
            collisionPadding={12}
            hideWhenDetached
            onEscapeKeyDown={(event) => event.stopPropagation()}
          >
            {content}
          </Primitive.Content>
        </Primitive.Portal>
      </Primitive.Root>
    </Primitive.Provider>
  );
}
