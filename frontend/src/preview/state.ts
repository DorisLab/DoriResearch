import { keyOf, type Reference, type Target } from '../types';

export interface Tabs {
  items: Target[];
  active: string;
}
export interface Draft {
  id: string;
  sourceKey: string;
  text: string;
  references: Reference[];
}
export interface Drafts {
  items: Draft[];
  active: string;
}
export const initialTabs: Tabs = { items: [], active: 'studio' };
export const initialDrafts: Drafts = { items: [], active: '' };

export function isTarget(value: unknown): value is Target {
  if (!value || typeof value !== 'object') return false;
  const target = value as Target;
  return (
    ['study', 'strategy', 'run', 'series'].includes(target.kind) &&
    [target.id, target.title, target.version].every((field) => typeof field === 'string')
  );
}
export function isTabs(value: unknown): value is Tabs {
  if (!value || typeof value !== 'object') return false;
  const state = value as Tabs;
  return (
    typeof state.active === 'string' && Array.isArray(state.items) && state.items.every(isTarget)
  );
}
export function isDrafts(value: unknown): value is Drafts {
  if (!value || typeof value !== 'object') return false;
  const drafts = value as Drafts;
  return (
    typeof drafts.active === 'string' && Array.isArray(drafts.items) && drafts.items.every(isDraft)
  );
}
function isDraft(value: unknown): value is Draft {
  if (!value || typeof value !== 'object') return false;
  const draft = value as Draft;
  return (
    [draft.id, draft.sourceKey, draft.text].every((field) => typeof field === 'string') &&
    Array.isArray(draft.references) &&
    draft.references.every((ref) => isTarget(ref?.source) && typeof ref.quote === 'string')
  );
}
export function openTab(state: Tabs, target: Target): Tabs {
  const key = keyOf(target);
  return {
    items: state.items.some((item) => keyOf(item) === key) ? state.items : [...state.items, target],
    active: key,
  };
}
export function closeTab(state: Tabs, key: string): Tabs {
  return {
    items: state.items.filter((item) => keyOf(item) !== key),
    active: state.active === key ? 'studio' : state.active,
  };
}
export function attachReference(state: Drafts, reference: Reference, newId: string): Drafts {
  const sourceKey = keyOf(reference.source);
  const existing = [...state.items].reverse().find((draft) => draft.sourceKey === sourceKey);
  const frozen = structuredClone(reference);
  if (existing)
    return {
      active: existing.id,
      items: state.items.map((draft) =>
        draft.id === existing.id ? { ...draft, references: [...draft.references, frozen] } : draft,
      ),
    };
  return {
    active: newId,
    items: [...state.items, { id: newId, sourceKey, text: '', references: [frozen] }],
  };
}
