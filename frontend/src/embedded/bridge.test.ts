import { expect, it, vi } from 'vitest';

it('coalesces frame pointer activity per paint and removes pending work on disconnect', async () => {
  const script = document.createElement('script');
  script.dataset.channel = 'pointer-test';
  script.dataset.parent = 'http://tauri.localhost';
  document.head.append(script);
  vi.resetModules();
  const { receive } = await import('./bridge');
  const post = vi.spyOn(parent, 'postMessage').mockImplementation(() => {});
  vi.useFakeTimers();
  const disconnect = receive(vi.fn());
  try {
    const menu = new MouseEvent('contextmenu', { cancelable: true });
    window.dispatchEvent(menu);
    expect(menu.defaultPrevented).toBe(true);
    window.dispatchEvent(new Event('pointermove'));
    window.dispatchEvent(new Event('pointermove'));
    expect(post).not.toHaveBeenCalled();
    vi.advanceTimersToNextFrame();
    expect(post).toHaveBeenCalledExactlyOnceWith(
      {
        protocol: 'dorislab.research.v1',
        channel: 'pointer-test',
        type: 'pointer-activity',
        payload: undefined,
      },
      'http://tauri.localhost',
    );
    window.dispatchEvent(new Event('pointermove'));
    disconnect();
    window.dispatchEvent(new Event('pointermove'));
    vi.advanceTimersToNextFrame();
    expect(post).toHaveBeenCalledOnce();
  } finally {
    disconnect();
    vi.useRealTimers();
    post.mockRestore();
    script.remove();
  }
});
