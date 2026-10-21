import { useState } from 'react';
import { Play, CaretDown } from '@phosphor-icons/react';
import type { BacktestConfig, PublicationRef } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { useBacktest, type Job } from './useBacktest';
import { BacktestFields, initialParameters } from './BacktestFields';

type Props = {
  config: BacktestConfig;
  reference: PublicationRef;
  host: ResearchHost;
  initial?: Record<string, unknown>;
};
export function BacktestPanel({ config, reference, host, initial = {} }: Props) {
  const [parameters, setParameters] = useState(() => initialParameters(config, initial));
  const [start, setStart] = useState(String(initial.start ?? config.date_range?.start ?? ''));
  const [end, setEnd] = useState(String(initial.end ?? config.date_range?.end ?? ''));
  const state = useBacktest(reference, host);
  return (
    <details className="backtest-panel">
      <summary>
        <CaretDown />
        {reference.kind === 'run' ? '沿用这次规则与参数重跑' : '回测这套策略'}
      </summary>
      <div className="backtest-panel-body">
        <p className="muted">本次参数只用于这次回测。完成后保存为独立结果，不会修改策略。</p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void state.run(parameters, start, end);
          }}
        >
          <fieldset disabled={state.running}>
            <BacktestFields
              {...{ config, parameters, setParameters, start, end, setStart, setEnd }}
            />
            <button className="quiet backtest-start" type="submit">
              <Play />
              {state.running ? '正在回测…' : '开始回测'}
            </button>
          </fieldset>
        </form>
        <JobStatus {...state} host={host} />
      </div>
    </details>
  );
}

function JobStatus({
  job,
  error,
  running,
  cancel,
  host,
}: {
  job?: Job;
  error: string;
  running: boolean;
  cancel: () => Promise<void>;
  host: ResearchHost;
}) {
  return (
    <>
      {running && job && (
        <button className="quiet" onClick={() => void cancel()}>
          取消回测
        </button>
      )}
      {(error || job?.error) && (
        <p role="alert" className="content-block-error">
          {error || job?.error}
        </p>
      )}
      {job?.result && (
        <button
          className="text-link"
          onClick={() => host.open({ ...job.result!, title: '策略回测结果' })}
        >
          查看已保存的回测结果 →
        </button>
      )}
    </>
  );
}
