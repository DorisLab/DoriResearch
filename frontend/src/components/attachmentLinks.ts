type Node = { type: string; value?: string; children?: Node[]; url?: string };

// Old reports often used an inline filename instead of a link. Only exact saved
// attachment names qualify; prose, code blocks and missing files are not guessed.
export function remarkAttachmentLinks({ paths }: { paths: string[] }) {
  const known = new Set(paths);
  return (tree: Node) => {
    const walk = (node: Node) => {
      if (node.type === 'link' || node.type === 'linkReference') return;
      node.children = node.children?.map((child) => {
        if (child.type === 'inlineCode' && child.value && known.has(child.value))
          return {
            type: 'link',
            url: encodeURIComponent(child.value).replaceAll('%2F', '/'),
            children: [{ type: 'text', value: child.value }],
          };
        walk(child);
        return child;
      });
    };
    walk(tree);
  };
}

export function attachmentPath(href: string | undefined, paths: string[]) {
  if (!href) return undefined;
  try {
    const decoded = decodeURIComponent(href).replace(/^\.\//, '');
    return paths.find((path) => path === decoded);
  } catch {
    return paths.find((path) => path === href);
  }
}
