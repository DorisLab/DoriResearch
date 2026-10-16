import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useBacktest } from './useBacktest';
import type { ResearchHost } from '../types';

const reference = { kind: 'strategy' as const, id: 'strategy', version: '1' };
const result = { kind: 'run' as const, id: 'result', version: '1' };
afterEach(() => {
  localStorage.clear();
  vi.useRealTimers();
});

it('opens a newly completed polled job once and does not reopen historical completion', async () => {
  const request = vi
    .fn()
    .mockResolvedValueOnce({ id: 'job', status: 'queued' })
    .mockResolvedValue({ id: 'job', status: 'succeeded', result });
  const host: ResearchHost = { protocolVersion: 1, request, open: vi.fn(), reference: vi.fn() };
  const hook = renderHook(() => useBacktest(reference, host));
  await waitFor(() => expect(hook.result.current.running).toBe(false));
  await act(() => hook.result.current.run({}, '', ''));
  await waitFor(() => expect(host.open).toHaveBeenCalledTimes(1));
  hook.unmount();
  renderHook(() => useBacktest(reference, host));
  await waitFor(() => expect(request).toHaveBeenCalledTimes(3));
  expect(host.open).toHaveBeenCalledTimes(1);
});

it.each(['failed', 'cancelled'])('does not open a %s job', async (status) => {
  const host: ResearchHost = {
    protocolVersion: 1,
    request: vi.fn().mockResolvedValue({ id: 'job', status, result }),
    open: vi.fn(),
    reference: vi.fn(),
  };
  const hook = renderHook(() => useBacktest(reference, host));
  await waitFor(() => expect(hook.result.current.running).toBe(false));
  await act(() => hook.result.current.run({}, '', ''));
  expect(hook.result.current.job?.status).toBe(status);
  expect(host.open).not.toHaveBeenCalled();
});
