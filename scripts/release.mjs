import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, readdir, lstat } from 'node:fs/promises';
import { resolve, relative } from 'node:path';
import { pathToFileURL } from 'node:url';

export function safe(name) {
  return !!name && !/[\\:%?#\x00-\x1f]/.test(name)
    && name.split('/').every(p => p && p !== '.' && p !== '..');
}
export function identity(files) {
  return createHash('sha256').update(JSON.stringify(Object.fromEntries(
    Object.entries(files).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0),
  ))).digest('hex');
}
export async function release(root, output) {
  const git = (...args) => execFileSync('git', ['-C', root, ...args], { encoding: 'utf8' }).trim();
  if (git('status', '--porcelain')) throw new Error('Commit and verify the release sources first');
  const commit = git('rev-parse', 'HEAD');
  const project = JSON.parse(await readFile(resolve(root, 'project.json'), 'utf8'));
  const files = {};
  // Refuse to overwrite an earlier release or write into the source tree.
  if (output === root || root.startsWith(output + '/')) throw new Error('Invalid release output');
  await mkdir(output, { recursive: false });
  async function copy(from, name) {
    if (!safe(name) || !(await lstat(from)).isFile()) throw new Error(`Unsafe file: ${name}`);
    const bytes = await readFile(from);
    await save(bytes, name);
  }
  async function save(bytes, name) {
    if (!safe(name)) throw new Error(`Unsafe file: ${name}`);
    await mkdir(resolve(output, name, '..'), { recursive: true });
    await writeFile(resolve(output, name), bytes);
    files[name] = createHash('sha256').update(bytes).digest('hex');
  }
  for (const name of git('ls-files', '-z').split('\0').filter(Boolean)) {
    if (name.split('/').some(p => p.startsWith('.env') || ['.npmrc', '.pypirc'].includes(p))) {
      throw new Error('Private configuration cannot be published');
    }
    // A clean Windows worktree can still contain CRLF while its commit contains LF.
    // Source and bundle must describe identical bytes, independent of checkout filters.
    const bytes = execFileSync('git', ['-C', root, 'show', `${commit}:${name}`], {
      maxBuffer: 32 * 1024 * 1024,
    });
    await save(bytes, `source/${name}`);
  }
  const build = resolve(root, 'frontend/dist/desktop');
  for (const entry of await readdir(build, { recursive: true, withFileTypes: true })) {
    if (entry.isSymbolicLink()) throw new Error('Build contains a link');
    if (entry.isFile()) {
      const file = resolve(entry.parentPath, entry.name);
      await copy(file, `build/${relative(build, file).replaceAll('\\', '/')}`);
    }
  }
  await mkdir(resolve(output, 'git'));
  const bundle = resolve(output, 'git/project.bundle');
  git('bundle', 'create', bundle, 'HEAD');
  git('bundle', 'verify', bundle);
  files['git/project.bundle'] = createHash('sha256').update(await readFile(bundle)).digest('hex');
  const sorted = Object.fromEntries(Object.entries(files).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
  await writeFile(resolve(output, 'release.json'), JSON.stringify({
    schema: 2, id: identity(sorted), version: project.version, host_protocol: 1,
    repository: 'https://github.com/DorisLab/DoriResearch.git', commit, files: sorted,
  }, null, 2));
  console.log(`DoriResearch ${project.version}: ${commit}, ${Object.keys(files).length} files`);
}
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const root = resolve(import.meta.dirname, '..');
  if (!process.argv[2]) throw new Error('Usage: node scripts/release.mjs <new output directory>');
  await release(root, resolve(process.argv[2]));
}
