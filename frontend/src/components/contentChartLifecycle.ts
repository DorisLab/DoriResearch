import type { DatasetComponentOption, EChartsOption, EChartsType } from 'echarts';
import type { Source } from './ContentBlock';
import { contentChartAppearance } from './contentChartAppearance';
import { contentChartOption } from './contentChartOption';

export async function loadChartContent({
  spec: value,
  host,
  reference,
  value: sourceValue,
}: Pick<Source, 'host' | 'reference' | 'value'> & { spec: unknown }) {
  const spec = value as {
    data?: string;
    columns?: string[];
    offset?: number;
    limit?: number;
    option?: EChartsOption;
  };
  const option = spec.option ?? (value as EChartsOption);
  if (!spec.data) return { option, rows: [] };
  const configPath = JSON.parse(sourceValue).src as string | undefined;
  const prefix = configPath?.includes('/')
    ? configPath.slice(0, configPath.lastIndexOf('/') + 1)
    : '';
  const dataset = await host.request!<NonNullable<DatasetComponentOption['source']>>('rows', {
    reference,
    path: prefix + spec.data,
    columns: spec.columns,
    offset: spec.offset,
    limit: spec.limit,
  });
  return {
    option: { ...option, dataset: { source: dataset } },
    rows: Array.isArray(dataset) ? (dataset as Record<string, unknown>[]) : [],
  };
}

function preserveInteraction(option: EChartsOption) {
  for (const zoom of Array.isArray(option.dataZoom) ? option.dataZoom : [option.dataZoom]) {
    if (!zoom) continue;
    delete zoom.start;
    delete zoom.end;
    delete zoom.startValue;
    delete zoom.endValue;
    delete zoom.rangeMode;
  }
  for (const legend of Array.isArray(option.legend) ? option.legend : [option.legend]) {
    if (legend) delete legend.selected;
  }
}

export function chartReflow(chart: EChartsType, target: HTMLElement) {
  let rendered = false;
  return (prepared: EChartsOption) => {
    const styles = getComputedStyle(document.documentElement);
    const option = contentChartOption(
      prepared,
      target.clientWidth,
      parseFloat(styles.getPropertyValue('--ui-font-size')) || 15,
      document.documentElement.dataset.theme === 'dark',
    );
    // 重排只改变样式和默认布局，不重新施加附件中的初始缩放与图例选择。
    if (rendered) preserveInteraction(option);
    chart.setOption(option);
    chart.setOption(contentChartAppearance(chart.getOption()));
    chart.resize();
    rendered = true;
  };
}
