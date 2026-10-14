import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { useStored } from './storage';

const valid = (value: unknown): value is string => typeof value === 'string';
beforeEach(() => localStorage.clear());
it('restores after mounting, then persists changes without overwriting the saved value first', async () => {
  localStorage.setItem('test.v1', JSON.stringify('saved'));
  const hook = renderHook(() => useStored('test.v1', 'default', valid));
  await waitFor(() => expect(hook.result.current[0]).toBe('saved'));
  act(() => hook.result.current[1]('updated'));
  expect(JSON.parse(localStorage.getItem('test.v1')!)).toBe('updated');
});
it('recovers from corrupt storage', async () => {
  localStorage.setItem('test.v1', '{broken');
  const hook = renderHook(() => useStored('test.v1', 'default', valid));
  await waitFor(() => expect(hook.result.current[2]).toBe(true));
  expect(hook.result.current[0]).toBe('default');
});
