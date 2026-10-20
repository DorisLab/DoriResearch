export interface ReadingSelection {
  text: string;
  range: Range;
}

export function readSelection(root: HTMLElement | null): ReadingSelection | null {
  const selection = root?.ownerDocument.getSelection();
  if (!root || !selection?.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) return null;
  const text = selectedText(root, range, selection);
  return text ? { text, range: range.cloneRange() } : null;
}
function selectedText(root: HTMLElement, range: Range, selection: Selection) {
  const code = root.querySelector('.file-code');
  const fragment = range.cloneContents();
  const insideCode = code?.contains(range.startContainer) && code.contains(range.endContainer);
  // Browser Selection.toString() drops a final blank code line. The source DOM
  // retains it, along with indentation; generated gutter numbers are not text.
  return insideCode || fragment.querySelector('.file-code')
    ? (fragment.textContent ?? '')
    : selection.toString();
}

export function restoreSelection(root: HTMLElement, value: ReadingSelection | null) {
  root.focus({ preventScroll: true });
  if (!value) return;
  const selection = root.ownerDocument.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(value.range);
}

export function selectReading(root: HTMLElement): ReadingSelection | null {
  const range = root.ownerDocument.createRange();
  range.selectNodeContents(root);
  restoreSelection(root, { text: '', range });
  return readSelection(root);
}

export function editingTarget(target: EventTarget | null) {
  return (
    target instanceof Element &&
    !!target.closest('input, textarea, select, [contenteditable="true"]')
  );
}

export async function copyReading(root: HTMLElement, value: ReadingSelection) {
  restoreSelection(root, value);
  // A user-initiated copy also works inside the sandboxed research document.
  if (root.ownerDocument.execCommand?.('copy')) return;
  await navigator.clipboard.writeText(value.text);
}
