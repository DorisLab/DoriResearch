import test from 'node:test';
import assert from 'node:assert/strict';
import { identity, safe, release } from './release.mjs';
import { mkdtemp, writeFile, readFile, mkdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';

test('release paths reject traversal and Windows alternate paths', () => {
  for (const value of ['', '../secret', '/root', 'a//b', 'a\\b', 'C:/file', 'a:stream', 'a/%2e']) {
    assert.equal(safe(value), false, value);
  }
  assert.equal(safe('.agents/skills/research-study/SKILL.md'), true);
});

test('release source equals Git bytes even when a clean checkout uses CRLF', async t => {
  const folder = await mkdtemp(join(tmpdir(), 'doriresearch-release-'));
  t.after(() => rm(folder, { recursive: true, force: true }));
  const source = join(folder, 'source');
  await mkdir(join(source, 'frontend/dist/desktop'), { recursive: true });
  const git = (...args) => execFileSync('git', ['-C', source, '-c', 'core.autocrlf=false',
    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
    ...args], { encoding: 'utf8' }).trim();
  await writeFile(join(source, '.gitattributes'), '* text=auto eol=lf\n');
  await writeFile(join(source, '.gitignore'), 'frontend/dist/\n');
  await writeFile(join(source, 'project.json'), '{"version":"0.3.0","host_protocol":2}\n');
  await writeFile(join(source, 'example.py'), 'print(1)\nprint(2)\n');
  await writeFile(join(source, 'frontend/dist/desktop/research.js'), '// fixture\n');
  git('init', '--quiet'); git('add', '.'); git('commit', '--quiet', '-m', 'fixture');
  await writeFile(join(source, 'example.py'), 'print(1)\r\nprint(2)\r\n');
  git('add', 'example.py');
  assert.equal(git('status', '--porcelain'), '');
  const output = join(folder, 'release');
  await release(source, output);
  assert.equal(await readFile(join(output, 'source/example.py'), 'utf8'), 'print(1)\nprint(2)\n');
  const manifest = JSON.parse(await readFile(join(output, 'release.json'), 'utf8'));
  assert.equal(manifest.commit, git('rev-parse', 'HEAD'));
  assert.equal(manifest.host_protocol, 2);
  assert.equal(manifest.id, identity(manifest.files));
  assert.ok((await readFile(join(output, 'git/project.bundle'))).length > 0);
});
test('release identity covers file names and bytes independent of insertion order', () => {
  assert.equal(identity({ b: '2', a: '1' }), identity({ a: '1', b: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ a: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ b: '1' }));
});
