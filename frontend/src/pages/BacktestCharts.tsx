import { useEffect, useMemo, useState } from 'react';
import type { PublicationContent } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { Chart } from '../components/Chart';
import { parseBacktestCharts, type BacktestCharts as ChartData } from '../backtestCharts';

function useChartData(host: ResearchHost, id: string, key: string, path?: string) {
  const [result, setResult] = useState<{ key: string; data: ChartData | null; error: string }>();
  useEffect(() => {
    let cancelled = false;
    if (path && host.readFile) {
      void host
        .readFile(path)
        .then((text) => {
          if (!cancelled) setResult({ key, data: parseBacktestCharts(text, id), error: '' });
        })
        .catch((cause) => {
          if (!cancelled)
            setResult({
              key,
              data: null,
              error: cause instanceof Error ? cause.message : String(cause),
            });
        });
    }
    return () => {
      cancelled = true;
    };
  }, [host, id, key, path]);
  return result?.key === key ? result : undefined;
}

export function BacktestCharts({
  content,
  host,
}: {
  content: PublicationContent;
  host: ResearchHost;
}) {
  const [attempt, setAttempt] = useState(0);
  const [metric, setMetric] = useState<'nav' | 'drawdown' | 'exposure'>('nav');
  const reference = content.item.reference;
  const path =
    reference.kind === 'run'
      ? ['charts.json', 'result.json'].find((name) =>
          content.files.some((file) => file.path === name),
        )
      : undefined;
  const result = useChartData(
    host,
    reference.id,
    `${reference.id}@${reference.version}:${attempt}`,
    path,
  );
  const data = result?.data;
  const runs = useMemo(
    () =>
      data ? [data.strategy, ...(metric === 'nav' && data.benchmark ? [data.benchmark] : [])] : [],
    [data, metric],
  );
  if (!path || !host.readFile) return null;
  if (!result) return <p role="status">正在读取运行曲线…</p>;
  if (result.error)
    return (
      <div className="source-note" role="alert">
        曲线暂不可用，正文仍可阅读。{result.error}
        <button onClick={() => setAttempt((value) => value + 1)}>重试</button>
      </div>
    );
  if (!data) return null;
  return (
    <section className="published-charts" aria-label="运行表现">
      <h2>运行表现</h2>
      <div className="chart-switch" role="group" aria-label="曲线指标">
        {(
          [
            ['nav', '净值'],
            ['drawdown', '回撤'],
            ['exposure', '仓位'],
          ] as const
        ).map(([value, label]) => (
          <button key={value} aria-pressed={metric === value} onClick={() => setMetric(value)}>
            {label}
          </button>
        ))}
      </div>
      <Chart
        runs={runs}
        metric={metric}
        source={{ ...reference, title: content.item.title }}
        onReference={host.reference}
      />
      <MonthlyReturns rows={data.monthly} />
    </section>
  );
}

function MonthlyReturns({ rows }: { rows: ChartData['monthly'] }) {
  return (
    <details>
      <summary>月收益</summary>
      <table>
        <thead>
          <tr>
            <th>月份</th>
            <th>收益</th>
            <th>覆盖</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.month}>
              <td>{row.month}</td>
              <td>{(row.return_rate * 100).toFixed(2)}%</td>
              <td>{row.complete ? '完整月' : '部分月'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className="muted">当前区间没有可计算的月收益。</p>}
    </details>
  );
}
