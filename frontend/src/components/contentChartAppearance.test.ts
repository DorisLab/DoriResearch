import { expect, it } from 'vitest';
import * as echarts from 'echarts';
import { contentChartAppearance } from './contentChartAppearance';

it('preserves authored multi-grid geometry and zoom targets when applying a theme', () => {
  const chart = echarts.init(null, undefined, {
    renderer: 'svg',
    ssr: true,
    width: 800,
    height: 360,
  });
  try {
    chart.setOption({
      animation: false,
      grid: [
        { top: 70, height: 80 },
        { top: 230, height: 65 },
      ],
      xAxis: [{ gridIndex: 0 }, { gridIndex: 1 }],
      yAxis: [{ gridIndex: 0 }, { gridIndex: 1 }],
      dataZoom: [
        { type: 'slider', xAxisIndex: [1], bottom: 5 },
        { type: 'inside', xAxisIndex: [1] },
      ],
      series: [
        {
          type: 'line',
          data: [
            [1, 2],
            [2, 3],
          ],
        },
        { type: 'scatter', xAxisIndex: 1, yAxisIndex: 1, data: [[1, 2]] },
      ],
    });
    const before = chart.getOption();
    chart.setOption(contentChartAppearance(before));
    const after = chart.getOption();
    expect(after.grid).toEqual(before.grid);
    expect(after.dataZoom).toMatchObject([
      { type: 'slider', xAxisIndex: [1], bottom: 5 },
      { type: 'inside', xAxisIndex: [1] },
    ]);
    expect(after.xAxis).toMatchObject([{ gridIndex: 0 }, { gridIndex: 1 }]);
    expect(after.yAxis).toMatchObject([{ gridIndex: 0 }, { gridIndex: 1 }]);
  } finally {
    chart.dispose();
  }
});

it('does not create Cartesian axes or zoom controls for a pie chart', () => {
  const themed = contentChartAppearance({ series: [{ type: 'pie' }] });
  expect(themed).not.toHaveProperty('grid');
  expect(themed).not.toHaveProperty('xAxis');
  expect(themed).not.toHaveProperty('yAxis');
  expect(themed).not.toHaveProperty('dataZoom');
});
