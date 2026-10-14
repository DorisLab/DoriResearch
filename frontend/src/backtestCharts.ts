import type { ChartSeries } from './components/Chart';

export interface BacktestCharts {
  strategy: ChartSeries;
  benchmark?: ChartSeries;
  monthly: { month: string; return_rate: number; complete: boolean }[];
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('运行曲线的数据结构无效');
  return value as Record<string, unknown>;
}
function number(value: unknown): number {
  if (typeof value !== 'number' || !Number.isFinite(value))
    throw new Error('运行曲线包含缺失或无效数值');
  return value;
}
function dates(values: unknown[], pattern: RegExp): string[] {
  if (!values.length || values.length > 20000) throw new Error('运行曲线的时间范围无效');
  return values.map((value, index) => {
    if (
      typeof value !== 'string' ||
      !pattern.test(value) ||
      (index > 0 && value <= String(values[index - 1]))
    )
      throw new Error('运行曲线的日期缺失、重复或顺序错误');
    return value;
  });
}
function series(rows: Record<string, unknown>[], id: string, label: string): ChartSeries {
  const values = rows.map((row) => number(row.nav));
  if (values.some((value) => value <= 0)) throw new Error('运行曲线的净值无效');
  return {
    id,
    variant: label,
    curve: {
      dates: dates(
        rows.map((row) => row.date),
        /^\d{4}-\d{2}-\d{2}$/,
      ),
      nav: values,
      drawdown: rows.map((row) => number(row.drawdown)),
      exposure: rows.map((row) => number(row.exposure)),
    },
  };
}
export function parseBacktestCharts(text: string, id: string): BacktestCharts | null {
  const input = record(JSON.parse(text));
  if (!['dorislab.backtest.result.v1', 'dorislab.backtest.chart.v1'].includes(String(input.schema)))
    return null;
  if (!Array.isArray(input.account) || !Array.isArray(input.monthly))
    throw new Error('运行曲线或月收益缺失');
  const strategy = series(input.account.map(record), id, '策略');
  strategy.role = 'strategy';
  if (
    strategy.curve.drawdown.some((value) => value > 1e-10 || value < -1) ||
    strategy.curve.exposure.some((value) => value < 0 || value > 1 + 1e-10)
  )
    throw new Error('回撤或仓位超出本策略的取值范围');
  const monthly = input.monthly.map((value) => {
    const row = record(value);
    if (typeof row.month !== 'string' || typeof row.complete !== 'boolean')
      throw new Error('月收益的区间状态缺失');
    return { month: row.month, return_rate: number(row.return_rate), complete: row.complete };
  });
  if (monthly.length)
    dates(
      monthly.map((row) => row.month),
      /^\d{4}-\d{2}$/,
    );
  return { strategy, benchmark: benchmark(input.benchmark, strategy), monthly };
}
function benchmark(value: unknown, strategy: ChartSeries): ChartSeries | undefined {
  const input = record(value);
  if (input.definition === 'none') return undefined;
  if (input.definition !== 'cash_zero' || !Array.isArray(input.curve))
    throw new Error('运行基准无法识别');
  const rows = input.curve.map((item) => ({ ...record(item), drawdown: 0, exposure: 0 }));
  const result = series(rows, `${strategy.id}:cash_zero`, '现金基准（零利息）');
  result.role = 'benchmark';
  if (
    JSON.stringify(result.curve.dates) !== JSON.stringify(strategy.curve.dates) ||
    result.curve.nav.some((nav) => nav !== 1)
  )
    throw new Error('现金基准与运行区间不一致');
  return result;
}
