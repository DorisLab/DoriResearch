import type { EChartsOption } from 'echarts';
import { chartTheme } from '../charting';

type Options = Record<string, unknown>;
const object = (value: unknown): Options =>
  value && typeof value === 'object' && !Array.isArray(value) ? (value as Options) : {};
function withDefaults(value: unknown, defaults: Options) {
  const authored = object(value);
  const result = { ...defaults, ...authored };
  // 固定尺寸与末端定位同时存在时，不补起点，避免改变 ECharts 的定位优先级。
  if (authored.width !== undefined && authored.right !== undefined && authored.left === undefined)
    delete result.left;
  if (authored.height !== undefined && authored.bottom !== undefined && authored.top === undefined)
    delete result.top;
  if (authored.outerBounds && authored.outerBoundsMode === undefined)
    result.outerBoundsMode = 'auto';
  return result;
}
const components = (value: unknown, defaults: Options) =>
  Array.isArray(value)
    ? value.map((item: unknown) => withDefaults(item, defaults))
    : withDefaults(value, defaults);

// 单个普通标题进入正文排版；多标题、链接标题仍由作者的 ECharts 布局负责。
export function chartHeading(option: EChartsOption) {
  const title = object(option?.title);
  if (title.show === false || title.link || title.sublink || typeof title.text !== 'string')
    return undefined;
  return { text: title.text, subtext: typeof title.subtext === 'string' ? title.subtext : '' };
}

function chartZoom(option: EChartsOption) {
  const cartesian = option.xAxis !== undefined && option.yAxis !== undefined;
  const xAxes = Array.isArray(option.xAxis) ? option.xAxis : [option.xAxis];
  return (
    option.dataZoom ??
    (cartesian &&
    xAxes.some(
      (axis) => axis?.type === 'category' || axis?.type === 'time' || (axis && 'data' in axis),
    )
      ? [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 2, showDetail: false }]
      : [])
  );
}

/** 只补充作者未指定的布局；显式网格、轴归属、缩放目标和颜色始终保留。 */
export function contentChartOption(
  option: EChartsOption,
  width: number,
  fontSize: number,
  dark: boolean,
): EChartsOption {
  const cartesian = option.xAxis !== undefined && option.yAxis !== undefined;
  const zoom = chartZoom(option);
  const sliders = (Array.isArray(zoom) ? zoom : [zoom]).some(
    (item) => item.type === 'slider' && (!('show' in item) || item.show !== false),
  );
  const axis = (value: unknown, horizontal: boolean) => {
    const defaults: Options = horizontal
      ? { nameLocation: 'middle', nameGap: fontSize }
      : { nameGap: fontSize, nameTextStyle: { align: 'left' } };
    const result = components(value, defaults);
    return (Array.isArray(result) ? result : [result]).map((item) => ({
      ...item,
      axisLabel: {
        hideOverlap: true,
        ...(horizontal && !object(item.axisLabel).rotate && !object(item.axisLabel).align
          ? {
              showMinLabel: true,
              showMaxLabel: true,
              alignMinLabel: item.inverse ? 'right' : 'left',
              alignMaxLabel: item.inverse ? 'left' : 'right',
            }
          : {}),
        ...object(item.axisLabel),
      },
      nameTextStyle: { ...object(defaults.nameTextStyle), ...object(item.nameTextStyle) },
    }));
  };
  const legend = components(option.legend, { type: 'scroll', top: 0, left: 0, right: 0 });
  const legends = (Array.isArray(legend) ? legend : [legend]).map((item) => ({
    ...item,
    textStyle: {
      width: Math.max(60, Math.min(width * 0.55, width - 110)),
      overflow: 'truncate',
      ...object(item.textStyle),
    },
    tooltip: { show: true, confine: true, renderMode: 'richText', ...object(item.tooltip) },
  }));
  return {
    animation: false,
    color: (dark ? chartTheme.dark : chartTheme).palette,
    ...option,
    ...(chartHeading(option) ? { title: [] } : {}),
    tooltip: {
      trigger: cartesian ? 'axis' : 'item',
      renderMode: 'richText',
      confine: true,
      ...object(option.tooltip),
    },
    legend: legends,
    ...(cartesian
      ? {
          grid: components(option.grid, {
            left: 8,
            right: 8,
            top: fontSize * 2 + 8,
            bottom: sliders ? 30 : 8,
            outerBoundsMode: 'same',
            outerBoundsContain: 'all',
          }),
          xAxis: axis(option.xAxis, true),
          yAxis: axis(option.yAxis, false),
          dataZoom: Array.isArray(zoom) ? zoom.map((item) => ({ ...item })) : { ...zoom },
        }
      : {}),
  } as EChartsOption;
}
