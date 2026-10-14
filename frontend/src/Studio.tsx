import { useCallback, useLayoutEffect, useRef } from 'react';
import { ResearchIcon } from './components/ResearchIcon';
import { StudyEntries, StrategyEntries } from './components/StudioEntries';
import { StudioRuns } from './components/StudioRuns';
import { StudioToolbar, StudioPagination } from './components/StudioToolbar';
import { useStored } from './storage';
import { initial, valid, listView, type ListState, type Section } from './studioState';
import { usePublicationPage } from './usePublicationPage';
import type { PublicationSummary } from './publicationContracts';
import type { ResearchHost } from './types';
const empty: PublicationSummary[] = [];
export function Studio({
  host,
  publications = empty,
}: {
  host: ResearchHost;
  publications?: PublicationSummary[];
}) {
  const [state, setState, restored] = useStored('dorislab.research.studio.v2', initial, valid);
  const scroll = useRef<HTMLDivElement>(null);
  const view = listView(state, publications);
  const { page, pending, error, retry } = usePublicationPage(
    host,
    {
      kind: state.section,
      query: view.query,
      series: state.section === 'study' ? view.series : '',
      sort: view.sort,
      page: view.page,
    },
    publications,
    restored,
  );
  const patch = useCallback(
    (value: Partial<ListState>) =>
      setState((current) => ({
        ...current,
        views: {
          ...current.views,
          [current.section]: { ...current.views[current.section], ...value },
        },
      })),
    [setState],
  );
  useLayoutEffect(() => {
    if (!restored || !page) return;
    if (page.page !== view.page) patch({ page: page.page });
    if (scroll.current) scroll.current.scrollTop = view.scroll;
  }, [restored, page, state.section, view.page, view.scroll, patch]);
  return (
    <div className="studio-shell">
      <div
        className="studio-scroll"
        ref={scroll}
        onScroll={(event) => {
          if (page) patch({ scroll: event.currentTarget.scrollTop });
        }}
      >
        <div className="studio-content">
          <StudioHeader
            section={state.section}
            change={(section) => setState((current) => ({ ...current, section }))}
          />
          <StudioToolbar
            section={state.section}
            view={view}
            series={publications.filter((p) => p.reference.kind === 'series')}
            change={(value) => patch({ ...value, page: 1, scroll: 0 })}
          />
          <StudioResults
            section={state.section}
            host={host}
            publications={publications}
            page={page}
            pending={pending}
            error={error}
            retry={retry}
            filtered={!!(view.query || view.series)}
            change={(next) => patch({ page: next, scroll: 0 })}
          />
        </div>
      </div>
    </div>
  );
}

function StudioHeader({ section, change }: { section: Section; change(section: Section): void }) {
  return (
    <header className="studio-header">
      <h1>
        <ResearchIcon kind="research-room" />
        我的研究室
      </h1>
      <nav className="studio-sections" aria-label="我的研究室板块">
        {(
          [
            { id: 'study', label: '研究' },
            { id: 'strategy', label: '策略' },
            { id: 'run', label: '运行' },
          ] as const
        ).map(({ id, label }) => (
          <button
            key={id}
            aria-current={section === id ? 'page' : undefined}
            onClick={() => change(id)}
          >
            <ResearchIcon kind={id} />
            {label}
          </button>
        ))}
      </nav>
    </header>
  );
}

function StudioResults({
  section,
  host,
  publications,
  page,
  pending,
  error,
  retry,
  filtered,
  change,
}: {
  section: Section;
  host: ResearchHost;
  publications: PublicationSummary[];
  page?: import('./types').PublicationPage;
  pending: boolean;
  error?: string;
  retry(): void;
  filtered: boolean;
  change(page: number): void;
}) {
  return (
    <div aria-busy={pending}>
      {error ? (
        <p role="alert">
          成果暂时无法读取。<button onClick={retry}>重试</button>
        </p>
      ) : page ? (
        <>
          {page.items.length === 0 ? (
            <p className="empty">{filtered ? '没有符合条件的成果。' : '还没有成果。'}</p>
          ) : (
            <>
              {section === 'study' && (
                <StudyEntries items={page.items} publications={publications} host={host} />
              )}
              {section === 'strategy' && (
                <StrategyEntries items={page.items} publications={publications} host={host} />
              )}
              {section === 'run' && (
                <StudioRuns items={page.items} publications={publications} host={host} />
              )}
            </>
          )}
          <StudioPagination total={page.total} page={page.page} change={change} />
        </>
      ) : (
        <p className="empty" role="status">
          正在读取成果…
        </p>
      )}
    </div>
  );
}
