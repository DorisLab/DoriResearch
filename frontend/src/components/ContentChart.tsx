import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { ChatCircleDots } from '@phosphor-icons/react';
import { connectChartView, type ChartView } from './chartView';
import { chartAppearance } from './chartAppearance';
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
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(target);
    const appearance = () => {
      const style = chartAppearance(false);
      if (!chart.getOption().xAxis) delete style.xAxis;
      if (!chart.getOption().yAxis) delete style.yAxis;
      chart.setOption(style);
    };
    void (async () => {
      const spec = value as { data?: string; option?: echarts.EChartsOption };
      const option = spec.option ?? (value as echarts.EChartsOption);
      let dataset: unknown;
      if (spec.data) {
        const configPath = JSON.parse(source.value).src as string | undefined;
        const prefix = configPath?.includes('/')
          ? configPath.slice(0, configPath.lastIndexOf('/') + 1)
          : '';
        dataset = await host.request!('rows', { reference, path: prefix + spec.data });
      }
      if (!current) return;
      chart.setOption({
        animation: false,
        color: ['#c4a565', '#6a9eb6', '#8ca58c', '#bd8077'],
        grid: { left: 18, right: 24, top: 40, bottom: 48, containLabel: true },
        tooltip: { trigger: 'axis', renderMode: 'richText', confine: true },
        legend: { top: 0 },
        dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 2 }],
        ...option,
        ...(dataset ? { dataset: { source: dataset } } : {}),
      });
      rows.current = Array.isArray(dataset) ? dataset : [];
      appearance();
      connectChartView(
        chart,
        view,
        `${reference.id}:${reference.version}:${source.value}`,
        Array.isArray(dataset) ? dataset.length : 1,
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
  return (
    <div className="content-chart chart-block">
      {error && <p role="alert">图表未能显示：{error}</p>}
      <div
        ref={element}
        className="content-chart-canvas chart-canvas"
        role="img"
        aria-label="交互研究图表"
      />
      <button
        className="chart-reference quiet"
        onClick={() =>
          host.reference(
            chartReference(
              { ...reference, title: title ?? '研究图表' },
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
  );
}
