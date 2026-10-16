import { useEffect, useRef, useState } from 'react';
import type { PublicationRef } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { useStored } from '../storage';

export type Job = { id: string; status: string; result?: PublicationRef; error?: string };
const validIdentity = (value: unknown): value is string | null =>
  value === null || typeof value === 'string';
export function useBacktest(reference: PublicationRef, host: ResearchHost) {
  const key = `doriresearch.backtest.${reference.id}.${reference.version}`;
  const [job, setJob] = useState<Job>();
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const requestId = useRef<string | null>(null);
  const [identity, setIdentity, restored] = useStored<string | null>(key, null, validIdentity);
  const running =
    !restored ||
    pending ||
    (!!identity && !job) ||
    job?.status === 'running' ||
    job?.status === 'queued';
  const waiting = !job || ['running', 'queued'].includes(job.status);
  useEffect(() => {
    if (!identity || !waiting) return;
    let current = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const value = await host.request!<Job>('job', { id: identity });
        if (!current) return;
        setJob(value);
        setError('');
        if (!['running', 'queued'].includes(value.status)) return;
      } catch (reason) {
        if (current) setError(`读取回测状态失败，正在重试：${String(reason)}`);
      }
      if (current) timer = setTimeout(() => void poll(), 1500);
    }
    void poll();
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [identity, waiting, host]);
  async function run(parameters: Record<string, string | number>, start: string, end: string) {
    setPending(true);
    setError('');
    setJob(undefined);
    requestId.current ??= crypto.randomUUID();
    try {
      const value = await host.request!<Job>('backtest', {
        reference,
        parameters,
        start,
        end,
        request_id: requestId.current,
      });
      setJob(value);
      setIdentity(value.id);
      requestId.current = null;
    } catch (reason) {
      setError(String(reason));
    } finally {
      setPending(false);
    }
  }
  async function cancel() {
    if (!identity) return;
    try {
      setJob(await host.request!<Job>('cancel_job', { id: identity }));
    } catch (reason) {
      setError(String(reason));
    }
  }
  return { job, error, running, run, cancel };
}
