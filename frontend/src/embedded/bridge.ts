import type { Target } from '../types';
import type { PublicationContent, PublicationSummary } from '../publicationContracts';
import { checkpointView } from '../viewCheckpoint';

export interface Appearance {
  theme: string;
  reducedMotion: boolean;
  variables: Record<string, string>;
}
export interface Init {
  related?: PublicationContent['related'];
  viewState?: unknown;
  lifecycle?: { archived: boolean; busy: boolean };
  publications?: PublicationSummary[];
  publication?: PublicationContent;
  target?: Target;
  storage: Record<string, string>;
  appearance: Appearance;
  shortcuts?: Record<string, string>;
}
const channel = document.querySelector('script[data-channel]')?.getAttribute('data-channel');
const parentOrigin = document.querySelector('script[data-parent]')?.getAttribute('data-parent');
export function send(type: string, payload?: unknown) {
  if (channel && parentOrigin)
    parent.postMessage({ protocol: 'dorislab.research.v1', channel, type, payload }, parentOrigin);
}
export function receive(callback: (type: string, payload: Init) => void) {
  const contextMenu = (event: MouseEvent) => event.preventDefault();
  window.addEventListener('contextmenu', contextMenu);
  let bindings: Record<string, string> = {};
  let pointerFrame: number | undefined;
  const pointer = () => {
    if (pointerFrame !== undefined) return;
    pointerFrame = requestAnimationFrame(() => {
      pointerFrame = undefined;
      send('pointer-activity');
    });
  };
  const shortcut = (event: KeyboardEvent) => {
    if (event.metaKey || event.isComposing || document.querySelector('[role="dialog"]')) return;
    const keys = shortcutKeys(event);
    const action = Object.keys(bindings).find((name) => bindings[name] === keys);
    if (!action) return;
    if (preserveEditing(keys, event)) return;
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) send('shortcut', action);
  };
  const listener = (event: MessageEvent) => {
    const message = event.data;
    if (!fromHost(event)) return;
    if (message.type === 'checkpoint-view' && typeof message.payload?.requestId === 'string') {
      send('view-checkpoint', { requestId: message.payload.requestId, ...checkpointView() });
      return;
    }
    if ((message.type === 'init' || message.type === 'shortcuts') && message.payload?.shortcuts)
      bindings = message.payload.shortcuts;
    callback(message.type, message.payload);
  };
  window.addEventListener('message', listener);
  window.addEventListener('keydown', shortcut, true);
  // The host cannot observe pointer moves inside this sandboxed frame. Coalesce
  // moves per paint so it can dismiss hover UI even when WebView2 omits mouseleave.
  window.addEventListener('pointermove', pointer, true);
  return () => {
    window.removeEventListener('contextmenu', contextMenu);
    window.removeEventListener('message', listener);
    window.removeEventListener('keydown', shortcut, true);
    window.removeEventListener('pointermove', pointer, true);
    if (pointerFrame !== undefined) cancelAnimationFrame(pointerFrame);
  };
}
export function fromHost(event: MessageEvent) {
  return (
    event.source === parent &&
    event.origin === parentOrigin &&
    event.data?.channel === channel &&
    event.data?.protocol === 'dorislab.research.v1'
  );
}
export function applyAppearance(value: Appearance) {
  document.documentElement.dataset.theme = value.theme;
  document.documentElement.dataset.motion = value.reducedMotion ? 'reduce' : 'full';
  for (const [key, setting] of Object.entries(value.variables)) {
    if (/^--[a-z-]+$/.test(key)) document.documentElement.style.setProperty(key, setting);
  }
  window.dispatchEvent(new Event('research-appearance'));
}

function shortcutKeys(event: KeyboardEvent) {
  const punctuation: Record<string, string> = {
    Comma: ',',
    Period: '.',
    Slash: '/',
    Semicolon: ';',
    Quote: "'",
    BracketLeft: '[',
    BracketRight: ']',
    Backslash: '\\',
    Minus: '-',
    Equal: '=',
    Backquote: '`',
  };
  const key = punctuation[event.code] ?? /^Digit([0-9])$/.exec(event.code)?.[1] ?? event.key;
  const named = key === ' ' ? 'Space' : key.length === 1 ? key.toUpperCase() : key;
  return [event.ctrlKey && 'Ctrl', event.altKey && 'Alt', event.shiftKey && 'Shift', named]
    .filter(Boolean)
    .join('+');
}

function preserveEditing(keys: string, event: KeyboardEvent) {
  return (
    keys === 'Ctrl+B' &&
    (event.target as Element)?.closest('input, textarea, [contenteditable="true"]')
  );
}
