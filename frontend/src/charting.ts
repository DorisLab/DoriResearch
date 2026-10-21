import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import theme from '../../backend/src/dorislab_research/chart_theme.json';

export type SeriesRole = 'strategy' | 'benchmark' | 'excess' | 'drawdown' | 'exposure';
export const chartTheme = theme;
export function seriesColor(role?: SeriesRole, index = 0) {
  return role ? theme[role] : theme.palette[index % theme.palette.length];
}

export interface ChartSpec {
  title: string;
  kind: 'line' | 'bar' | 'scatter';
  x: string[] | number[];
  x_label?: string;
  y_label?: string;
  series: { name: string; values: (number | null)[]; role?: SeriesRole }[];
}

export function chartOption(spec: ChartSpec): EChartsCoreOption {
  if (
    !spec.x.length ||
    !spec.series.length ||
    spec.series.some(
      (s) =>
        s.values.length !== spec.x.length ||
        s.values.some((n) => n !== null && !Number.isFinite(n)),
    )
  )
    throw new Error('图表序列须包含有限数值，并与横轴逐项对应');
  if (spec.kind === 'scatter' && spec.x.some((x) => typeof x !== 'number' || !Number.isFinite(x)))
    throw new Error('散点图需要数值横轴');
  return {
    animation: false,
    title: {
      text: spec.title,
      top: 8,
      left: 'center',
      textStyle: { fontSize: 18, lineHeight: 24 },
    },
    legend: { top: 44 },
    tooltip: { trigger: spec.kind === 'scatter' ? 'item' : 'axis' },
    grid: { containLabel: true, top: 88, left: 45, right: 25, bottom: 45 },
    xAxis: {
      type: spec.kind === 'scatter' ? 'value' : 'category',
      data: spec.kind === 'scatter' ? undefined : spec.x,
      name: spec.x_label,
    },
    yAxis: { type: 'value', name: spec.y_label, scale: true },
    series: spec.series.map((s, index) => ({
      name: s.name,
      type: spec.kind,
      connectNulls: false,
      data: spec.kind === 'scatter' ? s.values.map((value, i) => [spec.x[i], value]) : s.values,
      itemStyle: { color: seriesColor(s.role, index) },
      lineStyle: { color: seriesColor(s.role, index) },
    })),
  };
}

function exportBackground(chart: EChartsType): string {
  const explicit = chart.getOption().backgroundColor;
  if (typeof explicit === 'string' && explicit && explicit !== 'transparent') return explicit;
  return getComputedStyle(chart.getDom()).getPropertyValue('--canvas').trim() || '#fff';
}

function exportSvg(chart: EChartsType, background: string): string {
  // ECharts' SVG renderer ignores getDataURL's backgroundColor option.
  const document = new DOMParser().parseFromString(chart.renderToSVGString(), 'image/svg+xml');
  const backdrop = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  backdrop.setAttribute('width', '100%');
  backdrop.setAttribute('height', '100%');
  backdrop.setAttribute('fill', background);
  document.documentElement.prepend(backdrop);
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(new XMLSerializer().serializeToString(document))}`;
}

/** Export the displayed chart. SVG-to-PNG conversion uses the browser's canvas renderer. */
export async function exportChart(
  chart: EChartsType,
  format: 'svg' | 'png' = 'png',
): Promise<string> {
  const svg = !!chart.getDom()?.querySelector('svg');
  const backgroundColor = exportBackground(chart);
  if (!svg && format === 'svg') throw new Error('SVG 导出需要使用 ECharts SVGRenderer');
  if (!svg) return chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor });
  const source = exportSvg(chart, backgroundColor);
  if (format === 'svg') return source;
  const picture = new Image();
  picture.src = source;
  await picture.decode();
  const canvas = document.createElement('canvas');
  canvas.width = chart.getWidth() * 2;
  canvas.height = chart.getHeight() * 2;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('图表导出暂不可用');
  context.fillStyle = backgroundColor;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(picture, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/png');
}
