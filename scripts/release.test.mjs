import test from 'node:test';
import assert from 'node:assert/strict';
import { identity, safe } from './release.mjs';

test('release paths reject traversal and Windows alternate paths', () => {
  for (const value of ['', '../secret', '/root', 'a//b', 'a\\b', 'C:/file', 'a:stream', 'a/%2e']) {
    assert.equal(safe(value), false, value);
  }
  assert.equal(safe('.agents/skills/research-study/SKILL.md'), true);
});
test('release identity covers file names and bytes independent of insertion order', () => {
  assert.equal(identity({ b: '2', a: '1' }), identity({ a: '1', b: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ a: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ b: '1' }));
});
