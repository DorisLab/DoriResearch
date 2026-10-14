import { Fragment, useEffect, useRef, useState } from 'react';
import { Divider } from '../../ui/Divider';
import type { PublicationSummary } from '../publicationContracts';
import { type ResearchHost, type Target, percent } from '../types';
import { OpenLink } from './Common';
import { entryInteraction } from './EntryInteraction';
import { publicationLabel, referenceTarget, versionLabel } from './StudioEntries';
import { readRunOverview, type RunMetadataSource, type RunOverview } from './runOverview';

function RunCells({
  target,
  host,
  nature,
  strategies,
  overview,
  pending,
  error,
  retry,
}: {
  target: Target;
  host: ResearchHost;
  nature: string;
  strategies: Target[];
  overview: RunOverview;
  pending?: boolean;
  error?: boolean;
  retry?: () => void;
}) {
  const metric = (value?: number) => (value === undefined ? '—' : percent(value));
  return (
    <>
      <th scope="row">
        <OpenLink target={target} host={host} />
        {nature && <small>{nature}</small>}
      </th>
      <td>
        {strategies.length ? (
          strategies.map((target) => (
            <div key={`${target.id}@${target.version}`}>
              <OpenLink target={target} host={host}>
                {target.title} · {versionLabel(target.version)}
              </OpenLink>
            </div>
          ))
        ) : (
          <span className="muted">未关联策略</span>
        )}
      </td>
      <td className="run-period">
        {overview.start && overview.end ? (
          <>
            {overview.start.slice(0, 10)}
            <small>至 {overview.end.slice(0, 10)}</small>
          </>
        ) : (
          '未提供'
        )}
      </td>
      <td>
        <span>{pending ? '读取中…' : (overview.status ?? '未提供')}</span>
        {overview.created && (
          <small>{new Date(overview.created).toLocaleString('zh-CN', { hour12: false })}</small>
        )}
        {error && (
          <small role="status">
            运行信息暂不可用{' '}
            <button className="text-link" onClick={retry}>
              重试
            </button>
          </small>
        )}
      </td>
      <td className="run-metric">{metric(overview.totalReturn)}</td>
      <td className="run-metric">{metric(overview.maxDrawdown)}</td>
    </>
  );
}

function PublishedRun({
  item,
  publications,
  host,
}: {
  item: PublicationSummary;
  publications: PublicationSummary[];
  host: ResearchHost;
}) {
  const element = useRef<HTMLTableRowElement>(null);
  const metadataKey = JSON.stringify({
    reference: item.reference,
    project_format: item.project_format,
    files: item.files,
  });
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined');
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    overview: RunOverview;
    pending?: boolean;
    error?: boolean;
  }>({ overview: {}, pending: true });
  useEffect(() => {
    if (!element.current || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '150px' },
    );
    observer.observe(element.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible) return;
    let active = true;
    void readRunOverview(JSON.parse(metadataKey) as RunMetadataSource, host).then(
      (overview) => {
        if (active) setResult({ overview });
      },
      () => {
        if (active) setResult({ overview: {}, error: true });
      },
    );
    return () => {
      active = false;
    };
  }, [metadataKey, host, visible, attempt]);
  const strategies = (item.references ?? [])
    .filter((ref) => ref.kind === 'strategy')
    .map((ref) => referenceTarget(ref, publications));
  return (
    <tr ref={element} {...entryInteraction({ ...item.reference, title: item.title }, host)}>
      <RunCells
        target={{ ...item.reference, title: item.title }}
        host={host}
        nature={publicationLabel(item)}
        strategies={strategies}
        {...result}
        retry={() => {
          setResult({ overview: {}, pending: true });
          setAttempt((value) => value + 1);
        }}
      />
    </tr>
  );
}

export function StudioRuns({
  items,
  publications,
  host,
}: {
  items: PublicationSummary[];
  publications: PublicationSummary[];
  host: ResearchHost;
}) {
  const rows = items.map((item, index) => (
    <Fragment key={`${item.reference.id}@${item.reference.version}`}>
      {index > 0 && (
        <tr className="studio-run-divider" aria-hidden="true">
          <td colSpan={6}>
            <Divider />
          </td>
        </tr>
      )}
      <PublishedRun item={item} publications={publications} host={host} />
    </Fragment>
  ));
  if (!rows.length) return <p className="empty">还没有运行成果。</p>;
  return (
    <>
      <p className="run-list-note">先核对策略版本与数据区间，再比较结果。— 表示未提供指标。</p>
      <div
        className="table-scroll studio-run-table"
        role="region"
        aria-label="运行列表"
        tabIndex={0}
      >
        <table>
          <thead>
            <tr>
              <th>运行</th>
              <th>策略版本</th>
              <th>数据区间</th>
              <th>运行状态 / 时间</th>
              <th>区间收益</th>
              <th>最大回撤</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </>
  );
}
