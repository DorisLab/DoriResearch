import { describe, expect, it } from 'vitest';
import { attachReference, closeTab, initialDrafts, initialTabs, isTabs, openTab } from './state';
import { keyOf, objectReference, type Target } from '../types';

const study: Target = { kind: 'study', id: 'study', version: 'a', title: '研究 A' };
describe('versioned artifact tabs', () => {
  it('reuses a version, retains different versions and returns to studio after close', () => {
    const one = openTab(initialTabs, study);
    expect(openTab(one, { ...study, title: '新的展示标题' }).items).toHaveLength(1);
    const two = openTab(one, { ...study, version: 'b' });
    expect(two.items).toHaveLength(2);
    const closed = closeTab(two, two.active);
    expect(closed.active).toBe('studio');
    expect(closed.items[0].version).toBe('a');
  });
  it('rejects malformed saved tabs', () => {
    expect(isTabs({ items: [{ kind: 'file' }], active: 'studio' })).toBe(false);
  });
});
describe('frozen references and draft destinations', () => {
  it('preserves text and attachments when changing sources, including a new version', () => {
    const ref = objectReference(study);
    const first = attachReference(initialDrafts, ref, 'draft1');
    first.items[0].text = '保留这个问题';
    ref.quote = 'modified after attachment';
    expect(first.items[0].references[0].quote).toBe('研究 A');
    const other = attachReference(first, objectReference({ ...study, version: 'b' }), 'draft2');
    expect(other.active).toBe('draft2');
    expect(other.items[0].sourceKey).toBe(keyOf(study));
    const returned = attachReference(other, objectReference(study), 'unused');
    expect(returned.active).toBe('draft1');
    expect(returned.items[0].text).toBe('保留这个问题');
    expect(returned.items[0].references).toHaveLength(2);
    expect(returned.items).toHaveLength(2);
  });
});
