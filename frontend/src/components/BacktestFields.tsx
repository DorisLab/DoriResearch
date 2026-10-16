import type { BacktestConfig } from '../publicationContracts';

type Props = {
  config: BacktestConfig;
  parameters: Record<string, string | number>;
  setParameters: (value: Record<string, string | number>) => void;
  start: string;
  end: string;
  setStart: (value: string) => void;
  setEnd: (value: string) => void;
};
export function initialParameters(config: BacktestConfig, values: Record<string, unknown>) {
  return Object.fromEntries(
    config.parameters.map((item) => {
      const value = values[item.name];
      return [
        item.name,
        typeof value === 'number' || typeof value === 'string' ? value : item.default,
      ];
    }),
  );
}

export function BacktestFields({
  config,
  parameters,
  setParameters,
  start,
  end,
  setStart,
  setEnd,
}: Props) {
  return (
    <div className="backtest-fields">
      <label>
        开始日期
        <input
          type="date"
          value={start}
          min={config.date_range?.start}
          max={end || config.date_range?.end}
          onChange={(event) => setStart(event.target.value)}
        />
      </label>
      <label>
        结束日期
        <input
          type="date"
          value={end}
          min={start || config.date_range?.start}
          max={config.date_range?.end}
          onChange={(event) => setEnd(event.target.value)}
        />
      </label>
      {config.parameters.map((item) => (
        <Parameter
          key={item.name}
          item={item}
          value={parameters[item.name]}
          change={(value) => setParameters({ ...parameters, [item.name]: value })}
        />
      ))}
    </div>
  );
}
function Parameter({
  item,
  value,
  change,
}: {
  item: BacktestConfig['parameters'][number];
  value: string | number;
  change: (value: string | number) => void;
}) {
  return (
    <label>
      {item.label}
      {item.unit && `（${item.unit}）`}
      <input
        type={item.type}
        value={value}
        min={item.min}
        max={item.max}
        step={item.step}
        required
        onChange={(event) =>
          change(
            item.type === 'number' && event.target.value !== ''
              ? event.target.valueAsNumber
              : event.target.value,
          )
        }
      />
    </label>
  );
}
