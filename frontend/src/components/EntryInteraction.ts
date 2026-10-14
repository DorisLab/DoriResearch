import type { MouseEvent, KeyboardEvent } from 'react';
import type { ResearchHost, Target } from '../types';
export function entryInteraction(target: Target, host: ResearchHost) {
  return {
    tabIndex: 0,
    'aria-label': target.title,
    onClick(event: MouseEvent<HTMLElement>) {
      if (
        (event.target as Element).closest('button, a, input, [role="dialog"]') ||
        window.getSelection()?.toString()
      )
        return;
      host.open(target);
    },
    onKeyDown(event: KeyboardEvent<HTMLElement>) {
      if (event.target !== event.currentTarget || !['Enter', ' '].includes(event.key)) return;
      event.preventDefault();
      host.open(target);
    },
  };
}
