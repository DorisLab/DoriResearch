import test from 'node:test';
import assert from 'node:assert/strict';
import { identity, safe, release } from './release.mjs';
import { included, checkContent } from './release-content.mjs';
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
  await mkdir(join(source, 'backend'), { recursive: true });
  const git = (...args) => execFileSync('git', ['-C', source, '-c', 'core.autocrlf=false',
    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
    ...args], { encoding: 'utf8' }).trim();
  await writeFile(join(source, '.gitattributes'), '* text=auto eol=lf\n');
  await writeFile(join(source, '.gitignore'), 'frontend/dist/\n');
  await writeFile(join(source, 'project.json'), '{"version":"0.3.0","host_protocol":2}\n');
  await writeFile(join(source, 'backend/example.py'), 'print(1)\nprint(2)\n');
  await mkdir(join(source, 'docs/validation'), { recursive: true });
  await writeFile(join(source, 'docs/validation/internal.md'), 'private branch and build evidence\n');
  await writeFile(join(source, 'frontend/dist/desktop/research.js'), '// fixture\n');
  git('init', '--quiet'); git('add', '.'); git('commit', '--quiet', '-m', 'fixture');
  await writeFile(join(source, 'backend/example.py'), 'print(1)\r\nprint(2)\r\n');
  git('add', 'backend/example.py');
  assert.equal(git('status', '--porcelain'), '');
  git('rm', 'docs/validation/internal.md');
  git('commit', '--quiet', '-m', 'remove internal record from current tree');
  const output = join(folder, 'release');
  await release(source, output);
  assert.equal(await readFile(join(output, 'source/backend/example.py'), 'utf8'), 'print(1)\nprint(2)\n');
  const manifest = JSON.parse(await readFile(join(output, 'release.json'), 'utf8'));
  assert.equal(manifest.source_commit, git('rev-parse', 'HEAD'));
  assert.equal(manifest.source_policy, 'research-source-v1');
  assert.notEqual(manifest.commit, manifest.source_commit);
  assert.equal(manifest.host_protocol, 2);
  assert.equal(manifest.id, identity(manifest.files));
  assert.ok((await readFile(join(output, 'git/project.bundle'))).length > 0);
  const unpacked = join(folder, 'unpacked.git');
  execFileSync('git', ['init', '--bare', '--quiet', unpacked]);
  const check = (...args) => execFileSync('git', ['-C', unpacked, ...args], { encoding: 'utf8' }).trim();
  check('fetch', join(output, 'git/project.bundle'), 'HEAD');
  assert.equal(check('rev-parse', 'FETCH_HEAD'), manifest.commit);
  const allObjects = check('rev-list', '--objects', manifest.commit);
  assert.equal(allObjects.includes('docs/validation'), false);
  assert.equal(check('show', `${manifest.commit}:backend/example.py`), 'print(1)\nprint(2)');
});
test('release identity covers file names and bytes independent of insertion order', () => {
  assert.equal(identity({ b: '2', a: '1' }), identity({ a: '1', b: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ a: '2' }));
  assert.notEqual(identity({ a: '1' }), identity({ b: '1' }));
});

test('distribution retains editable code and checks while excluding internal publishing records', () => {
  for (const name of ['backend/tests/test_service.py', 'frontend/src/main.tsx', 'run.py',
    'docs/charts.md', 'scripts/check.ps1', 'scripts/verify-charts.mjs', '.agents/skills/example/SKILL.md']) {
    assert.equal(included(name), true, name);
  }
  for (const name of ['docs/validation/charts-2026-10-27.md', 'docs/release-033-2026-11-01.md',
    '.github/workflows/quality.yml', 'scripts/release.mjs']) assert.equal(included(name), false, name);
});

test('content failures redact private values, check UTF-16 and keep normal loopback examples', () => {
  const secret = '-----BEGIN ' + 'PRIVATE KEY-----\n' + 'A'.repeat(64) + '\nsynthetic-sensitive-value';
  for (const value of [secret, 'E:\\RustProjects\\example\\source.rs', 'https://10.42.3.4/api']) {
    for (const bytes of [Buffer.from(value), Buffer.from(value, 'utf16le'), Buffer.from(value, 'utf16le').swap16()]) {
      assert.throws(() => checkContent('backend/code.py', bytes), error => {
        assert.match(error.message, /Release content rejected/);
        assert.equal(error.message.includes(value), false);
        assert.equal(error.message.includes('synthetic-sensitive-value'), false);
        return true;
      });
    }
  }
  assert.throws(() => checkContent('frontend/private.js.map', Buffer.from('{}')), /private-debug-artifact/);
  assert.throws(() => checkContent('build/private.js', Buffer.from('//# sourceMappingURL=data:application/json;base64,aaa')), /private-source-map/);
  checkContent('backend/example.py', Buffer.from('http://127.0.0.1:1234 https://example.invalid /home/fly/notebook'));
  assert.throws(() => checkContent('backend/example.py', Buffer.from('/home/builder/projects/private/src')), /developer-path/);
  assert.throws(() => checkContent('backend/example.py', Buffer.from('/build/custom-root/private'), ['/build/custom-root']), /developer-path/);
});
