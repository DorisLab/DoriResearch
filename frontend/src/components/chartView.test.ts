// @vitest-environment node
import { expect, it, vi } from 'vitest';
import type { EChartsType } from 'echarts';
import { connectChartView, type ChartView } from './chartView';
import { initializeView, writeView } from '../viewCheckpoint';

it('uses authored initial ranges and selection without overwriting other zoom components', () => {
  initializeView({ schema: 1, values: {}, scroll: 0 }, {});
  const dispatchAction = vi.fn();
  const chart = {
    getOption: () => ({
      dataZoom: [
        { start: 5, end: 95 },
        { start: 40, end: 60 },
      ],
      legend: [{ selected: { 基准: false } }],
    }),
    on: vi.fn(),
    dispatchAction,
  } as unknown as EChartsType;
  const view = { current: { index: 0, zoom: [0, 100], hidden: [] } as ChartView };
  connectChartView(chart, view, 'authored', 10);
  expect(view.current).toEqual({ index: 0, zoom: [5, 95], hidden: ['基准'] });
  expect(dispatchAction).not.toHaveBeenCalled();

  writeView('chart:authored', { index: 3, zoom: [20, 70], hidden: [] });
  connectChartView(chart, view, 'authored', 10);
  expect(dispatchAction).toHaveBeenCalledWith({
    type: 'dataZoom',
    dataZoomIndex: 0,
    start: 20,
    end: 70,
  });
  expect(dispatchAction).toHaveBeenCalledWith({ type: 'legendSelect', name: '基准' });
});
