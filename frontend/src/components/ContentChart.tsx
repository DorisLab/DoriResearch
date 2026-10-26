import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { ChatCircleDots } from '@phosphor-icons/react';
import { connectChartView, type ChartView } from './chartView';
import { chartHeading } from './contentChartOption';
import { chartReflow, loadChartContent } from './contentChartLifecycle';
import { chartReference } from './chartReference';
import type { Source } from './ContentBlock';

function useContentChart({ spec: value, host, reference, ...source }: Source & { spec: unknown }) {
  const element = useRef<HTMLDivElement>(null);
  const rows = useRef<Record<string, unknown>[]>([]);
  const view = useRef<ChartView>({ index: 0, zoom: [0, 100], hidden: [] });
  const [error, setError] = useState('');
  useEffect(() => {
    const target = element.current;
    if (!target) return;
    let current = true;
    setError('');
    const chart = echarts.init(target, undefined, { renderer: 'svg' });
    let prepared: echarts.EChartsOption | undefined;
    const reflow = chartReflow(chart, target);
    const appearance = () => {
      if (!prepared) return;
      try {
        reflow(prepared);
      } catch (reason) {
        setError(String(reason));
      }
    };
    const observer = new ResizeObserver(appearance);
    observer.observe(target);
    void (async () => {
      const content = await loadChartContent({ spec: value, host, reference, value: source.value });
      if (!current) return;
      prepared = content.option;
      rows.current = content.rows;
      appearance();
      connectChartView(
        chart,
        view,
        `${reference.id}:${reference.version}:${source.value}`,
        Math.max(1, content.rows.length),
      );
    })().catch((reason: unknown) => {
      if (current) setError(String(reason));
    });
    window.addEventListener('research-appearance', appearance);
    return () => {
      current = false;
      observer.disconnect();
      chart.dispose();
      window.removeEventListener('research-appearance', appearance);
    };
  }, [value, host, reference, source.value]);
  return { element, rows, view, error };
}

export function ContentChart(props: Source & { spec: unknown }) {
  const { element, rows, view, error } = useContentChart(props);
  const { host, reference, title, value } = props;
  const spec = (props.spec ?? {}) as { option?: echarts.EChartsOption };
  const heading = chartHeading(spec.option ?? (spec as echarts.EChartsOption));
  return (
    <div className="content-chart chart-block">
      {error && <p role="alert">图表未能显示：{error}</p>}
      <div className="content-chart-header">
        {heading && (
          <div className="content-chart-heading">
            <strong>{heading.text}</strong>
            {heading.subtext && <p>{heading.subtext}</p>}
          </div>
        )}
        <button
          className="chart-reference quiet"
          onClick={() =>
            host.reference(
              chartReference(
                { ...reference, title: heading?.text || title || '研究图表' },
                value,
                rows.current,
                view.current,
              ),
            )
          }
        >
          <ChatCircleDots />
          引用图表
        </button>
      </div>
      <div
        ref={element}
        className="content-chart-canvas chart-canvas"
        role="img"
        aria-label={heading?.text || '交互研究图表'}
      />
    </div>
  );
}
