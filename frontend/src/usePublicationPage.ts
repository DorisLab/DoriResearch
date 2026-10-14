import { useEffect, useState } from 'react';
import type { PublicationPage, PublicationQuery, ResearchHost } from './types';
export function usePublicationPage(
  host: ResearchHost,
  request: PublicationQuery,
  revision: unknown,
  enabled: boolean,
) {
  const key = JSON.stringify(request);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ key: string; page?: PublicationPage; error?: string }>();
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const timer = window.setTimeout(() => {
      setPending(true);
      const promise =
        host.queryPublications?.(JSON.parse(key)) ??
        Promise.resolve({ items: [], total: 0, page: 1 });
      void promise.then(
        (page) => {
          if (active) {
            setResult({ key, page });
            setPending(false);
          }
        },
        (cause) => {
          if (active) {
            setResult({ key, error: String(cause) });
            setPending(false);
          }
        },
      );
    }, 150);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [host, key, revision, enabled, attempt]);
  const current = result?.key === key ? result : undefined;
  return {
    page: current?.page,
    error: current?.error,
    pending: pending || !current,
    retry: () => setAttempt((n) => n + 1),
  };
}
