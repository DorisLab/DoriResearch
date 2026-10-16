import { useState } from 'react';

interface Snapshot {
  schema: 1;
  values: Record<string, unknown>;
  scroll: number;
}
let state: Snapshot = { schema: 1, values: {}, scroll: 0 };
let pending = 0;
let storage: Record<string, string> = {};
export function trackViewRequest() {
  pending++;
  return () => {
    pending--;
  };
}
export function initializeView(value: unknown, cache: Record<string, string>) {
  storage = cache;
  if (value && typeof value === 'object' && (value as Snapshot).schema === 1) {
    const saved = value as Snapshot;
    if (saved.values && typeof saved.values === 'object' && Number.isFinite(saved.scroll))
      state = saved;
    const savedStorage = (value as { storage?: Record<string, string> }).storage;
    if (typeof savedStorage?.['dorislab.research.studio.v2'] === 'string')
      cache['dorislab.research.studio.v2'] = savedStorage['dorislab.research.studio.v2'];
  }
}
export function readView<T>(key: string, initial: T, valid: (value: unknown) => value is T): T {
  const value = state.values[key];
  return valid(value) ? value : initial;
}
export function writeView(key: string, value: unknown) {
  state.values[key] = value;
}
export function useViewChoice<T extends string>(key: string, initial: T, options: readonly T[]) {
  const [value, setValue] = useState(() =>
    readView(key, initial, (v): v is T => options.includes(v as T)),
  );
  return [
    value,
    (next: T) => {
      writeView(key, next);
      setValue(next);
    },
  ] as const;
}
export function checkpointView() {
  const scroll = document.querySelector('.artifact-scroll');
  if (scroll?.clientHeight) state.scroll = scroll.scrollTop;
  return {
    safe: pending === 0 && !document.querySelector('[role="dialog"], [contenteditable="true"]'),
    state: { ...state, storage },
  };
}
export function restoreViewScroll() {
  let frame = 0;
  let done = false;
  const remember = (event: Event) => {
    const element = event.target;
    if (
      done &&
      element instanceof HTMLElement &&
      element.matches('.artifact-scroll') &&
      element.clientHeight
    )
      state.scroll = element.scrollTop;
  };
  document.addEventListener('scroll', remember, true);
  const restore = () => {
    if (done) return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      const scroll = document.querySelector('.artifact-scroll');
      if (
        !scroll?.clientHeight ||
        pending ||
        scroll.scrollHeight < state.scroll + scroll.clientHeight
      )
        return;
      scroll.scrollTop = state.scroll;
      done = true;
      observer.disconnect();
    });
  };
  const observer = new MutationObserver(restore);
  observer.observe(document.body, { subtree: true, childList: true });
  restore();
  return () => {
    document.removeEventListener('scroll', remember, true);
    cancelAnimationFrame(frame);
    observer.disconnect();
  };
}
