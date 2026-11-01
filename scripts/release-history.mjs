import { execFileSync } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { included, checkContent } from './release-content.mjs';

const options = { maxBuffer: 128 * 1024 * 1024, windowsHide: true };
export function entries(root, commit) {
  return execFileSync('git', ['-C', root, 'ls-tree', '-rz', '--full-tree', commit],
    { ...options, encoding: 'utf8' }).split('\0').filter(Boolean).map(record => {
    const tab = record.indexOf('\t');
    const [mode, type, oid] = record.slice(0, tab).split(' ');
    return { mode, type, oid, name: record.slice(tab + 1) };
  }).filter(entry => included(entry.name));
}

function blobs(root, wanted) {
  const result = new Map();
  if (!wanted.length) return result;
  const bytes = execFileSync('git', ['-C', root, 'cat-file', '--batch'],
    { ...options, input: wanted.join('\n') + '\n' });
  let offset = 0;
  for (const oid of wanted) {
    const end = bytes.indexOf(10, offset);
    const [actual, type, length] = bytes.subarray(offset, end).toString().split(' ');
    if (actual !== oid || type !== 'blob' || !/^\d+$/.test(length)) throw new Error('Invalid source object');
    offset = end + 1;
    result.set(oid, bytes.subarray(offset, offset + Number(length)));
    offset += Number(length) + 1;
  }
  return result;
}

export async function filteredBundle(root, commit, destination) {
  const history = execFileSync('git', ['-C', root, 'rev-list', '--reverse', '--topo-order', '--parents', commit],
    { ...options, encoding: 'utf8' }).trim().split('\n').map(line => line.trim().split(' '));
  const snapshots = history.map(([id, ...parents]) => ({ id, parents, entries: entries(root, id) }));
  const objects = blobs(root, [...new Set(snapshots.flatMap(snapshot => snapshot.entries.map(entry => entry.oid)))]);
  const checked = new Set();
  for (const snapshot of snapshots) {
    for (const entry of snapshot.entries) {
      if (entry.type !== 'blob' || !['100644', '100755'].includes(entry.mode)) throw new Error('Unsafe source mode');
      const key = entry.name + ':' + entry.oid;
      if (!checked.has(key)) { checkContent(entry.name, objects.get(entry.oid)); checked.add(key); }
    }
  }
  const temporary = await mkdtemp(join(tmpdir(), 'doriresearch-distribution-'));
  try {
    execFileSync('git', ['init', '--bare', '--quiet', temporary], options);
    const stream = [];
    const marks = new Map();
    let next = 1;
    for (const [oid, bytes] of objects) {
      marks.set(oid, next++);
      stream.push(Buffer.from(`blob\nmark :${marks.get(oid)}\ndata ${bytes.length}\n`), bytes, Buffer.from('\n'));
    }
    const commits = new Map();
    for (const snapshot of snapshots) {
      commits.set(snapshot.id, next++);
      const message = 'DoriResearch distribution source\n';
      stream.push(Buffer.from(`commit refs/heads/release\nmark :${commits.get(snapshot.id)}\n`
        + 'author DoriResearch Release <release@dorislab.app> 0 +0000\n'
        + 'committer DoriResearch Release <release@dorislab.app> 0 +0000\n'
        + `data ${Buffer.byteLength(message)}\n${message}`));
      snapshot.parents.forEach((parent, index) => stream.push(Buffer.from(`${index ? 'merge' : 'from'} :${commits.get(parent)}\n`)));
      stream.push(Buffer.from('deleteall\n'));
      for (const entry of snapshot.entries) stream.push(Buffer.from(`M ${entry.mode} :${marks.get(entry.oid)} ${JSON.stringify(entry.name)}\n`));
      stream.push(Buffer.from('\n'));
    }
    execFileSync('git', ['-C', temporary, 'fast-import', '--quiet'], { ...options, input: Buffer.concat(stream) });
    execFileSync('git', ['-C', temporary, 'symbolic-ref', 'HEAD', 'refs/heads/release'], options);
    execFileSync('git', ['-C', temporary, 'bundle', 'create', destination, 'HEAD'], options);
    execFileSync('git', ['-C', temporary, 'bundle', 'verify', destination], options);
    return execFileSync('git', ['-C', temporary, 'rev-parse', 'HEAD'], { ...options, encoding: 'utf8' }).trim();
  } finally { await rm(temporary, { recursive: true, force: true }); }
}
