import { expect, test, vi } from 'vitest';
import {
  initializeView,
  readView,
  writeView,
  checkpointView,
  trackViewRequest,
  restoreViewScroll,
} from './viewCheckpoint';

test('restores per-page values and navigation; keeps pending requests resident', () => {
  const storage: Record<string, string> = {};
  initializeView(
    {
      schema: 1,
      values: { metric: 'drawdown' },
      scroll: 90,
      storage: { 'dorislab.research.studio.v2': '{"section":"run"}' },
    },
    storage,
  );
  expect(readView('metric', 'nav', (v): v is string => typeof v === 'string')).toBe('drawdown');
  expect(storage['dorislab.research.studio.v2']).toContain('run');
  const finish = trackViewRequest();
  expect(checkpointView().safe).toBe(false);
  finish();
  writeView('metric', 'exposure');
  expect(checkpointView()).toMatchObject({
    safe: true,
    state: { scroll: 90, values: { metric: 'exposure' } },
  });
});

test('initial layout scroll cannot overwrite the saved position while content loads', async () => {
  initializeView({ schema: 1, values: {}, scroll: 120 }, {});
  document.body.innerHTML = '<div class="artifact-scroll"></div>';
  const element = document.querySelector<HTMLElement>('.artifact-scroll')!;
  Object.defineProperties(element, { clientHeight: { value: 100 }, scrollHeight: { value: 500 } });
  const finish = trackViewRequest();
  const cleanup = restoreViewScroll();
  element.dispatchEvent(new Event('scroll'));
  finish();
  element.append(document.createElement('p'));
  await vi.waitFor(() => expect(element.scrollTop).toBe(120));
  element.scrollTop = 250;
  element.dispatchEvent(new Event('scroll'));
  expect(checkpointView().state.scroll).toBe(250);
  cleanup();
  document.body.innerHTML = '';
});
