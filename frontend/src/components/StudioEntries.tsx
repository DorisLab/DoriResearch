import { SavedTime } from './SavedTime';
import type { PublicationRef, PublicationSummary } from '../publicationContracts';
import { type ResearchHost, type Target } from '../types';
import { ResearchIcon } from './ResearchIcon';
import { OpenLink } from './Common';
import { PublicationCover } from './PublicationCover';
import { entryInteraction } from './EntryInteraction';
import { SeparatedEntries } from './SeparatedEntries';

export const sameReference = (a: PublicationRef, b: PublicationRef) =>
  a.kind === b.kind && a.id === b.id && a.version === b.version;
export const publicationLabel = (item: PublicationSummary) =>
  [
    item.origin === 'example' ? '示例' : '',
    item.data_nature === 'synthetic'
      ? '使用模拟数据'
      : item.data_nature === 'mixed'
        ? '含模拟数据'
        : '',
  ]
    .filter(Boolean)
    .join(' · ');

export function referenceTarget(ref: PublicationRef, items: PublicationSummary[]): Target {
  const item = items.find(
    (item) => item.reference.kind === ref.kind && item.reference.id === ref.id,
  );
  const kind = { study: '研究', strategy: '策略', run: '运行', series: '系列' }[ref.kind];
  return { ...(item?.reference ?? ref), title: item?.title ?? `关联${kind}已不可用` };
}

export function EntryTitle({ target, host }: { target: Target; host: ResearchHost }) {
  return (
    <h2>
      <button className="title-link" onClick={() => host.open(target)}>
        <ResearchIcon kind={target.kind} />
        {target.title}
      </button>
    </h2>
  );
}

function studySeries(item: PublicationSummary, publications: PublicationSummary[]) {
  const refs = (item.references ?? []).filter((ref) => ref.kind === 'series');
  for (const series of publications.filter((p) => p.reference.kind === 'series')) {
    if (
      series.references?.some((ref) => ref.kind === 'study' && ref.id === item.reference.id) &&
      !refs.some((ref) => ref.id === series.reference.id)
    )
      refs.push(series.reference);
  }
  return refs;
}

export function StudyEntries({
  items,
  publications = [],
  host,
}: {
  items: PublicationSummary[];
  publications?: PublicationSummary[];
  host: ResearchHost;
}) {
  return (
    <SeparatedEntries className="study-list">
      {items.map((item) => (
        <article
          {...entryInteraction({ ...item.reference, title: item.title }, host)}
          className="study-card published-card"
          key={`${item.reference.id}@${item.reference.version}`}
        >
          <div className="study-copy">
            <EntryTitle target={{ ...item.reference, title: item.title }} host={host} />
            <p>{item.summary || '暂无摘要'}</p>
            <div className="entry-meta">
              {publicationLabel(item) && <span>{publicationLabel(item)}</span>}
              <SavedTime value={item.registered_at} />
              {studySeries(item, publications).map((ref) => (
                <OpenLink key={ref.id} target={referenceTarget(ref, publications)} host={host} />
              ))}
            </div>
          </div>
          {item.cover && host.readCover && <PublicationCover item={item} host={host} />}
        </article>
      ))}
    </SeparatedEntries>
  );
}

export function StrategyEntries({
  items,
  publications,
  host,
}: {
  items: PublicationSummary[];
  publications: PublicationSummary[];
  host: ResearchHost;
}) {
  return (
    <SeparatedEntries className="strategy-list">
      {items.map((item) => {
        const studies = [
          ...new Map(
            (item.references ?? [])
              .filter((ref) => ref.kind === 'study')
              .map((ref) => [ref.id, ref]),
          ).values(),
        ];
        const count = publications.filter(
          (run) =>
            run.reference.kind === 'run' &&
            run.references?.some((ref) => ref.kind === 'strategy' && ref.id === item.reference.id),
        ).length;
        return (
          <article
            {...entryInteraction({ ...item.reference, title: item.title }, host)}
            className="strategy-row"
            key={`${item.reference.id}@${item.reference.version}`}
          >
            <div>
              <EntryTitle target={{ ...item.reference, title: item.title }} host={host} />
              <p>{item.summary || '暂无规则摘要'}</p>
              <div className="entry-meta">
                <SavedTime value={item.registered_at} />
                {publicationLabel(item) && <span>{publicationLabel(item)}</span>}
                <span>{count} 次运行</span>
              </div>
              <div className="entry-relations">
                {studies.length ? (
                  studies.map((ref) => (
                    <OpenLink
                      key={`${ref.id}@${ref.version}`}
                      target={referenceTarget(ref, publications)}
                      host={host}
                    >
                      {referenceTarget(ref, publications).title}
                    </OpenLink>
                  ))
                ) : (
                  <span>未关联研究</span>
                )}
              </div>
            </div>
          </article>
        );
      })}
    </SeparatedEntries>
  );
}
