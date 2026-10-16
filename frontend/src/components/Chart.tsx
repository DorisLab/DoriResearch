import { useEffect, useRef } from 'react';
import { init, use as registerCharts, type EChartsCoreOption } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import { ChatCircleDots } from '@phosphor-icons/react';
import type { Reference, Target } from '../types';
import { chartAppearance } from './chartAppearance';
import { seriesColor, type SeriesRole } from '../charting';
import { connectChartView, type ChartView as View } from './chartView';

registerCharts([
  LineChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  SVGRenderer,
]);
type Metric = 'nav' | 'drawdown' | 'exposure';
export interface ChartSeries {
  id: string;
  variant: string;
  curve: { dates: string[]; nav: number[]; drawdown: number[]; exposure: number[] };
  role?: SeriesRole;
}
interface Props {
  runs: ChartSeries[];
  compact?: boolean;
  metric?: Metric;
  source?: Target;
  onReference?: (reference: Reference) => void;
}

function option(runs: ChartSeries[], compact: boolean, metric: Metric): EChartsCoreOption {
  const dates = runs[0]?.curve.dates ?? [];
  const daily = new Set(dates.map((date) => date.slice(0, 7))).size < dates.length;
  return {
    animation: false,
    color: runs.map((run, index) =>
      seriesColor(run.role === 'strategy' && metric !== 'nav' ? metric : run.role, index),
    ),
    legend: {
      type: 'scroll',
      show: !compact,
      top: 0,
      icon: 'roundRect',
      itemWidth: 16,
      itemHeight: 3,
    },
    tooltip: {
      trigger: 'axis',
      renderMode: 'richText',
      confine: true,
      valueFormatter: (value: number) =>
        metric === 'nav' ? value.toFixed(4) : `${(value * 100).toFixed(2)}%`,
    },
    xAxis: {
      type: 'category',
      data: runs[0]?.curve.dates,
      boundaryGap: false,
      axisLabel: {
        color: '#6f767d',
        formatter: (value: string) => (daily ? value : value.slice(0, 7)),
        hideOverlap: true,
      },
      axisLine: { lineStyle: { color: '#dfe4e8' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitNumber: 3,
      axisLabel: {
        color: '#6f767d',
        formatter: (value: number) =>
          metric === 'nav' ? value.toFixed(2) : `${Math.round(value * 100)}%`,
      },
      splitLine: { lineStyle: { color: '#e8edf0', type: 'dashed' } },
    },
    dataZoom: compact
      ? []
      : [
          { type: 'inside', filterMode: 'none' },
          { type: 'slider', height: 18, bottom: 6, borderColor: 'transparent', brushSelect: false },
        ],
    series: runs.map((run, index) => ({
      name: run.variant,
      type: 'line',
      data: run.curve[metric],
      symbol: 'none',
      lineStyle: { width: index === runs.length - 1 ? 2.5 : 1.5 },
      emphasis: { focus: 'series' },
    })),
  };
}

function makeReference(source: Target, runs: ChartSeries[], metric: Metric, view: View): Reference {
  const date = runs[0].curve.dates[view.index];
  return {
    schemaVersion: 1,
    source,
    kind: 'chart',
    locator: `chart:${metric}`,
    createdAt: new Date().toISOString(),
    quote: `${metric === 'nav' ? '净值' : metric === 'drawdown' ? '回撤' : '仓位'}对照 · ${date}`,
    chart: {
      metric,
      runIds: source.kind === 'run' ? [source.id] : runs.map((run) => run.id),
      date,
      zoom: [...view.zoom],
      hidden: [...view.hidden],
      values: Object.fromEntries(runs.map((run) => [run.id, run.curve[metric][view.index]])),
    },
  };
}

export function Chart({ runs, compact = false, metric = 'nav', source, onReference }: Props) {
  const element = useRef<HTMLDivElement>(null);
  const view = useRef<View>({ index: 0, zoom: [0, 100], hidden: [] });
  useEffect(() => {
    if (!element.current || !runs.length) return;
    view.current = { index: runs[0].curve.dates.length - 1, zoom: [0, 100], hidden: [] };
    const chart = init(element.current, undefined, { renderer: 'svg' });
    chart.setOption(option(runs, compact, metric));
    const appearance = () => {
      chart.setOption(chartAppearance(compact));
      // Font loading and appearance changes must not reset zoom or legend selection.
      const styles = getComputedStyle(document.body);
      void document.fonts
        .load(`${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`)
        .then(() => {
          if (!chart.isDisposed()) chart.resize();
        });
    };
    appearance();
    window.addEventListener('research-appearance', appearance);
    connectChartView(
      chart,
      view,
      `${source?.id ?? 'preview'}:${metric}`,
      runs[0].curve.dates.length,
    );
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element.current);
    return () => {
      window.removeEventListener('research-appearance', appearance);
      observer.disconnect();
      chart.dispose();
    };
  }, [runs, compact, metric, source?.id]);
  if (!runs.length) return <p className="muted">暂无曲线</p>;
  return (
    <div className={`chart-block ${compact ? 'compact' : ''}`}>
      <div
        ref={element}
        className="chart-canvas"
        role="img"
        aria-label={`${metric} 对照曲线；精确指标见下方结果表`}
      />
      {source && onReference && (
        <button
          className="chart-reference quiet"
          onClick={() => onReference(makeReference(source, runs, metric, view.current))}
        >
          <ChatCircleDots />
          引用图表
        </button>
      )}
    </div>
  );
}
