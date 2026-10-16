import { useEffect, useState } from 'react';
import type { PublicationRef, PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

export function StrategyResults({
  reference,
  host,
}: {
  reference: PublicationRef;
  host: ResearchHost;
}) {
  const [items, setItems] = useState<PublicationSummary[]>([]);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  useEffect(() => {
    let current = true;
    const load = () =>
      void host.request!<PublicationSummary[]>('results', { reference })
        .then((value) => {
          if (current) {
            setItems(value);
            setError('');
          }
        })
        .catch((reason: unknown) => {
          if (current) setError(String(reason));
        });
    load();
    const timer = setInterval(load, 5000);
    return () => {
      current = false;
      clearInterval(timer);
    };
  }, [reference, host]);
  if (error) return <p role="alert">回测结果未能读取：{error}</p>;
  if (!items.length) return null;
  return (
    <section className="strategy-results" aria-label="已保存的回测结果">
      <h2>回测结果</h2>
      <p className="muted">每次结果单独保存，点击查看当时的参数与表现。</p>
      {items.slice((page - 1) * 20, page * 20).map((item) => (
        <button
          className="strategy-result-row"
          key={item.reference.id}
          onClick={() => host.open({ ...item.reference, title: item.title })}
        >
          <strong>{item.title}</strong>
          <span>{item.summary}</span>
          <small>{new Date(item.registered_at).toLocaleString()}</small>
        </button>
      ))}
      {items.length > 20 && (
        <nav className="content-table-pagination" aria-label="回测结果分页">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}>
            上一页
          </button>
          <span>
            {page} / {Math.ceil(items.length / 20)}
          </span>
          <button disabled={page * 20 >= items.length} onClick={() => setPage(page + 1)}>
            下一页
          </button>
        </nav>
      )}
    </section>
  );
}
