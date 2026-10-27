// @vitest-environment node
import { expect, it } from 'vitest';
import * as echarts from 'echarts';
import { contentChartOption, chartHeading } from './contentChartOption';
import { chartOption } from '../charting';

it('keeps zero and whole-number intervals for integer bars in the rendered scale', () => {
  const chart = echarts.init(null, undefined, {
    renderer: 'svg',
    ssr: true,
    width: 352,
    height: 360,
  });
  try {
    chart.setOption(
      contentChartOption(
        chartOption({
          title: '事件次数',
          kind: 'bar',
          x: ['甲', '乙', '丙'],
          series: [{ name: '次数', values: [1, 2, 3] }],
        }),
        352,
        15,
        false,
      ),
    );
    const svg = chart.renderToSVGString();
    expect(svg).toContain('>0</text>');
    expect(svg).not.toMatch(/>\d+\.5<\/text>/);
  } finally {
    chart.dispose();
  }
});

it('preserves explicit multi-grid layout, axis assignment, colors and zoom state through themes', () => {
  const original: echarts.EChartsOption = {
    color: ['#123456'],
    grid: [
      { top: 40, height: 60, containLabel: true },
      { top: 180, height: 60 },
    ],
    xAxis: [
      { type: 'category', gridIndex: 0 },
      { type: 'category', gridIndex: 1 },
    ],
    yAxis: [{ gridIndex: 0, min: -5, max: 5 }, { gridIndex: 1 }],
    dataZoom: [{ type: 'slider', xAxisIndex: [1], start: 20, end: 70, bottom: 7 }],
    series: [
      { type: 'line', data: [1, 2, 3] },
      { type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: [4, 3, 2] },
    ],
  };
  const chart = echarts.init(null, undefined, {
    renderer: 'svg',
    ssr: true,
    width: 600,
    height: 360,
  });
  try {
    chart.setOption(contentChartOption(original, 600, 15, false));
    chart.setOption(contentChartOption(original, 400, 18, true));
    expect(chart.getOption()).toMatchObject({
      color: ['#123456'],
      grid: [
        { top: 40, height: 60 },
        { top: 180, height: 60 },
      ],
      xAxis: [{ gridIndex: 0 }, { gridIndex: 1 }],
      yAxis: [{ min: -5, max: 5 }, {}],
      dataZoom: [{ xAxisIndex: [1], start: 20, end: 70, bottom: 7 }],
    });
  } finally {
    chart.dispose();
  }
});

it('does not invent axes or zoom for non-Cartesian charts and only extracts plain single titles', () => {
  const pie = contentChartOption(
    { series: [{ type: 'pie', data: [{ value: 1, name: '甲' }] }] },
    352,
    18,
    true,
  );
  expect(pie).not.toHaveProperty('xAxis');
  expect(pie).not.toHaveProperty('grid');
  expect(pie).not.toHaveProperty('dataZoom');
  expect(chartHeading({ title: { text: '标题', subtext: '口径' } })).toEqual({
    text: '标题',
    subtext: '口径',
  });
  expect(chartHeading({ title: [{ text: '上' }, { text: '下' }] })).toBeUndefined();
  expect(chartHeading({ title: { text: '链接', link: 'https://example.com' } })).toBeUndefined();
});

it('keeps end-anchored fixed-size layouts and explicit outer bounds', () => {
  const option = contentChartOption(
    {
      grid: { width: 240, right: 12, height: 100, bottom: 50, outerBounds: { left: 0, right: 0 } },
      xAxis: { type: 'category' },
      yAxis: { type: 'value' },
      legend: { width: 200, right: 5 },
      series: [],
    },
    600,
    15,
    false,
  );
  expect(option.grid).toMatchObject({
    width: 240,
    right: 12,
    height: 100,
    bottom: 50,
    outerBoundsMode: 'auto',
  });
  expect(option.grid).not.toHaveProperty('left');
  expect(option.grid).not.toHaveProperty('top');
  expect(option.legend).toMatchObject([{ width: 200, right: 5 }]);
  expect((option.legend as unknown[])[0]).not.toHaveProperty('left');
});
