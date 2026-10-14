import { expect, test } from 'vitest';
import { parseBacktestCharts } from './backtestCharts';

const result = () => ({
  schema: 'dorislab.backtest.result.v1',
  account: [
    { date: '2025-01-30', nav: 1, drawdown: 0, exposure: 0 },
    { date: '2025-01-31', nav: 1.02, drawdown: 0, exposure: 0.5 },
    { date: '2025-02-03', nav: 0.99, drawdown: -0.0294117647, exposure: 0.49 },
  ],
  monthly: [
    { month: '2025-01', return_rate: 0.02, complete: false },
    { month: '2025-02', return_rate: -0.0294117647, complete: false },
  ],
  benchmark: {
    definition: 'cash_zero',
    curve: [
      { date: '2025-01-30', nav: 1 },
      { date: '2025-01-31', nav: 1 },
      { date: '2025-02-03', nav: 1 },
    ],
  },
});

test.each(['dorislab.backtest.chart.v1', 'dorislab.backtest.result.v1'])(
  'reads frozen daily values and partial months from %s',
  (schema) => {
    const parsed = parseBacktestCharts(JSON.stringify({ ...result(), schema }), 'run-1')!;
    expect(parsed.strategy.curve.nav).toEqual([1, 1.02, 0.99]);
    expect(parsed.strategy.curve.drawdown.at(-1)).toBe(-0.0294117647);
    expect(parsed.monthly[0]).toEqual({ month: '2025-01', return_rate: 0.02, complete: false });
    expect(parsed.benchmark?.curve.nav).toEqual([1, 1, 1]);
  },
);
test('unsupported formats keep the report without manufacturing a curve', () => {
  expect(parseBacktestCharts('{"schema":"custom.v2"}', 'run-1')).toBeNull();
});
test('rejects missing values, duplicate dates, negative NAV and misaligned benchmarks', () => {
  for (const corrupt of [
    (value: ReturnType<typeof result>) => {
      value.account[0].nav = null as unknown as number;
    },
    (value: ReturnType<typeof result>) => {
      value.account[1].date = value.account[0].date;
    },
    (value: ReturnType<typeof result>) => {
      value.account[1].nav = -1;
    },
    (value: ReturnType<typeof result>) => {
      value.benchmark.curve.pop();
    },
    (value: ReturnType<typeof result>) => {
      value.account[1].exposure = 2;
    },
  ]) {
    const input = result();
    corrupt(input);
    expect(() => parseBacktestCharts(JSON.stringify(input), 'run-1')).toThrow();
  }
});
