import { SavedTime } from '../components/SavedTime';
import { publicationLabel } from '../components/StudioEntries';
import type { PublicationContent } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { PageHeader } from '../components/Common';
import { RelatedPublications } from '../components/RelatedPublications';
import { PublicationFiles } from '../../ui/PublicationFiles';
import { TextSelection } from '../components/TextSelection';
import { BacktestPanel } from '../components/BacktestPanel';
import { StrategyResults } from '../components/StrategyResults';
import { PublishedMarkdown } from './PublishedMarkdown';

export const kindLabel = { study: '研究', strategy: '策略', run: '回测结果', series: '系列' };
export function PublishedPage({
  content,
  host,
}: {
  content: PublicationContent;
  host: ResearchHost;
}) {
  const { item } = content;
  const target = { ...item.reference, title: item.title };
  return (
    <div className="report-page research-content">
      <PageHeader
        target={target}
        host={host}
        summary={item.summary}
        metadata={
          <>
            {publicationLabel(item) && (
              <span className="source-mark">{publicationLabel(item)}</span>
            )}
            <span>
              更新于 <SavedTime value={item.registered_at} />
            </span>
          </>
        }
      />
      <RelatedPublications key={`${target.kind}:${target.id}`} content={content} host={host} />
      <main className="report-body published-body">
        <TextSelection source={target} host={host}>
          <section id="body">
            <PublishedMarkdown
              key={`${item.reference.kind}:${item.reference.id}@${item.reference.version}`}
              content={content}
              host={host}
            />
          </section>
        </TextSelection>
        {content.config?.backtest && (
          <BacktestPanel
            key={`${item.reference.id}:${item.reference.version}`}
            config={content.config.backtest}
            initial={content.config.parameters}
            reference={item.reference}
            host={host}
          />
        )}
        {item.reference.kind === 'strategy' && host.request && (
          <StrategyResults reference={item.reference} host={host} />
        )}
        {content.revision_note && <p className="revision-note">{content.revision_note}</p>}
        <PublicationFiles files={content.files} open={(path) => host.previewFile?.(path)} />
      </main>
    </div>
  );
}
