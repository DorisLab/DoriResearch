import type { PublicationContent } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { ResearchIcon } from './ResearchIcon';
import { useStored } from '../storage';

const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean';
const kinds = { study: '研究', strategy: '策略', run: '回测结果', series: '系列' };

export function RelatedPublications({
  content,
  host,
}: {
  content: PublicationContent;
  host: ResearchHost;
}) {
  const { kind, id } = content.item.reference;
  const [expanded, setExpanded] = useStored(
    `doriresearch.related.v1.${kind}.${id}`,
    false,
    isBoolean,
  );
  const items = content.related ?? [];
  if (!items.length) return null;
  return (
    <nav className="related-publications" aria-label="相关内容">
      <p className="muted">相关内容</p>
      <ul>
        {items.slice(0, expanded ? undefined : 3).map(({ reference, title, unavailable }) => (
          <li key={`${reference.kind}:${reference.id}`}>
            <button
              className="related-publication"
              disabled={unavailable}
              aria-label={`${kinds[reference.kind]}：${title}${unavailable ? '（已不可用）' : ''}`}
              onClick={() => host.open({ ...reference, title })}
            >
              <ResearchIcon kind={reference.kind} />
              <span>
                {title}
                {unavailable && <span className="muted">（已不可用）</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {items.length > 3 && (
        <button
          className="text-link"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '收起' : `展开其余 ${items.length - 3} 项`}
        </button>
      )}
    </nav>
  );
}
