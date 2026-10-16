import { chartAppearance } from './chartAppearance';

// Theme an authored chart without changing its grids, axes or zoom targets.
export function contentChartAppearance(option: Record<string, unknown>) {
  const theme = chartAppearance(false);
  const repeat = (value: unknown, style: unknown) =>
    (Array.isArray(value) ? value : [value]).map(() => style);
  const zoomStyle = Array.isArray(theme.dataZoom) ? theme.dataZoom[1] : {};
  return {
    textStyle: theme.textStyle,
    tooltip: theme.tooltip,
    ...(option.legend ? { legend: repeat(option.legend, theme.legend) } : {}),
    ...(option.xAxis ? { xAxis: repeat(option.xAxis, theme.xAxis) } : {}),
    ...(option.yAxis ? { yAxis: repeat(option.yAxis, theme.yAxis) } : {}),
    ...(Array.isArray(option.dataZoom)
      ? {
          dataZoom: option.dataZoom.map((zoom: { type?: string }) =>
            zoom.type === 'slider' ? zoomStyle : {},
          ),
        }
      : {}),
  };
}
