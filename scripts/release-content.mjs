// This fixed profile is also verified by the desktop's official-source merger.
const roots = ['.agents/', 'backend/', 'frontend/'];
const files = new Set(['.gitattributes', '.gitignore', '.node-version', '.python-version',
  'AGENTS.md', 'LICENSE', 'README.md', 'project.json', 'run.py', 'docs/charts.md',
  'scripts/check.ps1', 'scripts/dev.py', 'scripts/verify-charts.mjs', 'scripts/chart-fixture.tsx']);

export const sourcePolicy = 'research-source-v1';
export function included(name) {
  return files.has(name) || roots.some(root => name.startsWith(root));
}

export function checkContent(name, bytes) {
  const fail = (rule, offset = 0) => { throw new Error(`Release content rejected: ${rule}, ${name}, byte ${offset}`); };
  if (/\.(?:pdb|ilk|exp|dSYM|(?:js|css)\.map)$/i.test(name)) fail('private-debug-artifact');
  const views = [{ text: bytes.toString('utf8'), offset: index => Buffer.byteLength(bytes.toString('utf8').slice(0, index)) }];
  for (const alignment of [0, 1]) {
    const aligned = bytes.subarray(alignment, alignment + ((bytes.length - alignment) & ~1));
    views.push({ text: aligned.toString('utf16le'), offset: index => alignment + index * 2 });
    views.push({ text: Buffer.from(aligned).swap16().toString('utf16le'), offset: index => alignment + index * 2 });
  }
  for (const { text, offset } of views) {
    const rules = [
      ['private-key', /-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----|untrusted comment:[^\r\n]{0,80}(?:encrypted )?secret key/i],
      ['developer-path', /[a-z]:[\\/](?:RustProjects|Projects|Workspaces?|repos?)[\\/]|[a-z]:[\\/]Users[\\/][^\\/\s<>"']{1,80}[\\/]|\/(?:home|Users)\/[^/\s<>"']{1,80}\//i],
      ['internal-address', /\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|169\.254(?:\.\d{1,3}){2})\b/],
      ['internal-address', /\b(?:fc|fd)[0-9a-f]{2}(?::[0-9a-f]{0,4}){2,7}\b/i],
      ['internal-address', /(?:https?|wss?):\/\/[^/\s\0]{1,160}\.(?:lan|internal|local)(?=[:/\s\0]|$)/i],
    ];
    if (/\.(?:js|css|html)$/i.test(name)) rules.push(['private-source-map', /(?:\/\/[#@]|\/\*[#@])\s*sourceMappingURL\s*=/]);
    for (const [rule, pattern] of rules) {
      const match = pattern.exec(text);
      if (match) fail(rule, offset(match.index));
    }
  }
}
