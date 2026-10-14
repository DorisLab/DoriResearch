import type { PublicationSummary } from './publicationContracts';
export type Section = 'study' | 'strategy' | 'run';
export interface ListState {
  query: string;
  series: string;
  sort: string;
  page: number;
  scroll: number;
}
export interface StudioState {
  section: Section;
  views: Record<Section, ListState>;
}
const view = (): ListState => ({ query: '', series: '', sort: 'newest', page: 1, scroll: 0 });
export const initial: StudioState = {
  section: 'study',
  views: { study: view(), strategy: view(), run: view() },
};
export function valid(value: unknown): value is StudioState {
  if (!value || typeof value !== 'object') return false;
  const state = value as StudioState;
  return (
    ['study', 'strategy', 'run'].includes(state.section) &&
    !!state.views &&
    (['study', 'strategy', 'run'] as const).every((kind) => {
      const entry = state.views[kind];
      return (
        !!entry &&
        typeof entry.query === 'string' &&
        entry.query.length <= 120 &&
        typeof entry.series === 'string' &&
        ['newest', 'oldest', 'title'].includes(entry.sort) &&
        Number.isInteger(entry.page) &&
        entry.page > 0 &&
        Number.isFinite(entry.scroll) &&
        entry.scroll >= 0
      );
    })
  );
}

export function listView(state: StudioState, publications: PublicationSummary[]): ListState {
  const saved = state.views[state.section];
  const available = publications.some(
    (p) => p.reference.kind === 'series' && p.reference.id === saved.series,
  );
  return { ...saved, series: available ? saved.series : '' };
}
