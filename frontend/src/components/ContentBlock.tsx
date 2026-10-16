import { useEffect, useState } from 'react';
import type { PublicationRef } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { ContentChart } from './ContentChart';

export type Source = {
  title?: string;
  kind: string;
  value: string;
  reference: PublicationRef;
  host: ResearchHost;
};
type Metric = { label: string; value: string | number; unit?: string; description?: string };
function validMetric(value: unknown): value is Metric {
  if (!value || typeof value !== 'object') return false;
  const metric = value as Record<string, unknown>;
  return (
    typeof metric.label === 'string' &&
    ['string', 'number'].includes(typeof metric.value) &&
    (metric.unit === undefined || typeof metric.unit === 'string') &&
    (metric.description === undefined || typeof metric.description === 'string')
  );
}
type TableData = {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  page: number;
};

export function ContentBlock(source: Source) {
  const [value, setValue] = useState<unknown>();
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    Promise.resolve()
      .then(async () => {
        const input = JSON.parse(source.value);
        const result =
          source.kind === 'datatable' || !input.src
            ? input
            : JSON.parse(await source.host.readFile!(input.src));
        if (current) {
          setValue(result);
          setError('');
        }
      })
      .catch((reason: unknown) => {
        if (current) setError(String(reason));
      });
    return () => {
      current = false;
    };
  }, [source.kind, source.value, source.host]);
  if (error)
    return (
      <p className="content-block-error" role="alert">
        此处内容未能显示：{error}
      </p>
    );
  if (!value)
    return (
      <p className="muted" role="status">
        正在读取内容…
      </p>
    );
  if (source.kind === 'metrics') {
    if (!Array.isArray(value) || !value.every(validMetric))
      return <p role="alert">指标组应包含名称、数值及可选的单位和说明。</p>;
    return (
      <dl className="metric-group">
        {(value as Metric[]).map((metric, index) => (
          <div key={index}>
            <dt>{metric.label}</dt>
            <dd>
              {metric.value}
              <small>{metric.unit}</small>
            </dd>
            {metric.description && <p>{metric.description}</p>}
          </div>
        ))}
      </dl>
    );
  }
  if (source.kind === 'datatable')
    return <DataTable {...source} path={(value as { src: string }).src} />;
  return <ContentChart {...source} spec={value} />;
}

function DataTable({ path, reference, host }: Source & { path: string }) {
  const state = useTable(path, reference, host);
  const { query, setQuery, setPage, sort, setSort, descending, setDescending, data, error } = state;
  return (
    <section className="content-table" aria-label="研究数据">
      <div className="content-table-tools">
        <input
          aria-label="筛选表格"
          placeholder="筛选此表"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(1);
          }}
        />
        <span className="muted">{data ? `共 ${data.total} 行` : '正在读取…'}</span>
      </div>
      {error ? (
        <p role="alert">{error}</p>
      ) : (
        data && (
          <>
            <TableGrid
              data={data}
              sort={sort}
              descending={descending}
              onSort={(column) => {
                setSort(column);
                setDescending(sort === column && !descending);
                setPage(1);
              }}
            />
            {data.total > 20 && (
              <nav className="content-table-pagination" aria-label="表格分页">
                <button disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>
                  上一页
                </button>
                <span>
                  {data.page} / {Math.ceil(data.total / 20)}
                </span>
                <button
                  disabled={data.page * 20 >= data.total}
                  onClick={() => setPage(data.page + 1)}
                >
                  下一页
                </button>
              </nav>
            )}
          </>
        )
      )}
    </section>
  );
}

function useTable(path: string, reference: PublicationRef, host: ResearchHost) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('');
  const [descending, setDescending] = useState(false);
  const [data, setData] = useState<TableData>();
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(() => {
      void host.request!<TableData>('table', { reference, path, query, page, sort, descending })
        .then((value) => {
          if (current) {
            setData(value);
            setError('');
          }
        })
        .catch((reason: unknown) => {
          if (current) setError(String(reason));
        });
    }, 120);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [host, reference, path, query, page, sort, descending]);
  return { query, setQuery, setPage, sort, setSort, descending, setDescending, data, error };
}

function TableGrid({
  data,
  sort,
  descending,
  onSort,
}: {
  data: TableData;
  sort: string;
  descending: boolean;
  onSort: (column: string) => void;
}) {
  return (
    <div className="table-scroll" tabIndex={0}>
      <table>
        <thead>
          <tr>
            {data.columns.map((column) => (
              <th
                key={column}
                aria-sort={sort === column ? (descending ? 'descending' : 'ascending') : 'none'}
              >
                <button onClick={() => onSort(column)}>
                  {column}
                  {sort === column ? (descending ? ' ↓' : ' ↑') : ''}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, index) => (
            <tr key={index}>
              {data.columns.map((column) => (
                <td key={column}>
                  {typeof row[column] === 'number'
                    ? Number(row[column]).toLocaleString(undefined, {
                        maximumFractionDigits: 4,
                      })
                    : String(row[column] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
