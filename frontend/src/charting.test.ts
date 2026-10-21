import { expect, it } from 'vitest';
import { chartOption, seriesColor } from './charting';

it('assigns semantic colors independently of order or display names', () => {
  const options = chartOption({
    kind: 'line',
    title: 'comparison',
    x: ['a', 'b'],
    series: [
      { name: '市场', role: 'benchmark', values: [1, 2] },
      { name: '方案', role: 'strategy', values: [2, null] },
    ],
  });
  expect(options.series).toMatchObject([
    { data: [1, 2], itemStyle: { color: '#477bb5' } },
    { data: [2, null], connectNulls: false, itemStyle: { color: '#c83932' } },
  ]);
  expect(seriesColor('drawdown')).toBe('#df8a87');
  expect(() =>
    chartOption({
      kind: 'scatter',
      title: 'invalid',
      x: ['a'],
      series: [{ name: 'x', values: [1] }],
    }),
  ).toThrow();
});
