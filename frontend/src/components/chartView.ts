import type { EChartsType } from 'echarts/core';
import type { RefObject } from 'react';
import { readView, writeView } from '../viewCheckpoint';

export interface ChartView {
  index: number;
  zoom: [number, number];
  hidden: string[];
}
function valid(value: unknown): value is ChartView {
  const v = value as ChartView | null;
  return (
    !!v &&
    Number.isInteger(v.index) &&
    v.index >= 0 &&
    Array.isArray(v.zoom) &&
    v.zoom.length === 2 &&
    v.zoom.every((n) => Number.isFinite(n) && n >= 0 && n <= 100) &&
    v.zoom[0] <= v.zoom[1] &&
    Array.isArray(v.hidden) &&
    v.hidden.every((n) => typeof n === 'string')
  );
}
function restoreChartView(chart: EChartsType, saved: ChartView) {
  const option = chart.getOption();
  if ((option.dataZoom as unknown[] | undefined)?.length) {
    chart.dispatchAction({
      type: 'dataZoom',
      dataZoomIndex: 0,
      start: saved.zoom[0],
      end: saved.zoom[1],
    });
  }
  const legends = (option.legend as { selected?: Record<string, boolean> }[] | undefined) ?? [];
  for (const name of legends.flatMap((legend) => Object.keys(legend.selected ?? {}))) {
    if (!saved.hidden.includes(name)) chart.dispatchAction({ type: 'legendSelect', name });
  }
  for (const name of saved.hidden) chart.dispatchAction({ type: 'legendUnSelect', name });
}
export function connectChartView(
  chart: EChartsType,
  view: RefObject<ChartView>,
  key: string,
  length: number,
) {
  const option = chart.getOption();
  const zoom = (option.dataZoom as { start?: number; end?: number }[] | undefined)?.[0];
  const legends = (option.legend as { selected?: Record<string, boolean> }[] | undefined) ?? [];
  const initial: ChartView = {
    index: 0,
    zoom: [zoom?.start ?? 0, zoom?.end ?? 100],
    hidden: [
      ...new Set(
        legends.flatMap((legend) =>
          Object.entries(legend.selected ?? {})
            .filter(([, selected]) => !selected)
            .map(([name]) => name),
        ),
      ),
    ],
  };
  const saved = readView(`chart:${key}`, initial, valid);
  view.current = { ...saved, index: Math.min(saved.index, length - 1) };
  const persist = () => writeView(`chart:${key}`, { ...view.current });
  chart.on('updateAxisPointer', (raw: unknown) => {
    const index = (raw as { axesInfo?: { value: number }[] }).axesInfo?.[0]?.value;
    if (typeof index === 'number') {
      view.current.index = index;
      persist();
    }
  });
  chart.on('datazoom', () => {
    const zoom = chart.getOption().dataZoom as { start: number; end: number }[];
    if (!zoom?.[0]) return;
    view.current.zoom = [zoom[0].start, zoom[0].end];
    persist();
  });
  chart.on('legendselectchanged', (raw: unknown) => {
    const event = raw as { selected: Record<string, boolean> };
    view.current.hidden = Object.keys(event.selected).filter((name) => !event.selected[name]);
    persist();
  });
  // Restore through public chart actions so the displayed chart and reference snapshot agree.
  if (saved !== initial) restoreChartView(chart, saved);
  persist();
}
