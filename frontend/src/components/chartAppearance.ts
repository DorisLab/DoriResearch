import type { EChartsCoreOption } from 'echarts/core';

export function chartAppearance(compact: boolean): EChartsCoreOption {
  const styles = getComputedStyle(document.documentElement);
  const read = (key: string, fallback: string) => styles.getPropertyValue(key).trim() || fallback;
  const text = read('--text', '#24282c');
  const muted = read('--muted', '#60666d');
  const line = read('--line', '#dfe4e8');
  const surface = read('--surface', '#f5f6f7');
  const fontSize = parseFloat(read('--ui-font-size', '15px'));
  const typography = {
    fontFamily: read('--font-ui', 'Segoe UI, sans-serif'),
    fontSize,
    fontWeight: Number(read('--font-ui-weight', '400')),
    fontStyle: read('--font-ui-style', 'normal') as 'normal' | 'italic' | 'oblique',
  };
  return {
    textStyle: { ...typography, color: text },
    grid: {
      containLabel: true,
      left: 8,
      right: 16,
      top: compact ? 18 : fontSize * 3.2,
      bottom: compact ? 8 : fontSize * 3.5,
    },
    legend: { textStyle: { ...typography, color: text }, inactiveColor: muted },
    tooltip: {
      backgroundColor: read('--canvas', '#fff'),
      borderColor: line,
      textStyle: { ...typography, color: text },
    },
    xAxis: { axisLabel: { ...typography, color: muted }, axisLine: { lineStyle: { color: line } } },
    yAxis: {
      axisLabel: { ...typography, color: muted },
      splitLine: { lineStyle: { color: line } },
    },
    dataZoom: compact
      ? []
      : [
          {},
          {
            textStyle: { ...typography, color: muted },
            backgroundColor: surface,
            fillerColor: 'rgba(196, 165, 101, .18)',
            borderColor: line,
            handleStyle: { color: '#c4a565', borderColor: '#c4a565' },
            dataBackground: { areaStyle: { color: muted } },
          },
        ],
  };
}
