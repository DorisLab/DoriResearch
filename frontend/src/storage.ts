import { useEffect, useState } from 'react';

let researchStorage: Pick<Storage, 'getItem' | 'setItem'> | undefined;
export function setResearchStorage(storage: Pick<Storage, 'getItem' | 'setItem'>) {
  researchStorage = storage;
}
const storage = () => researchStorage ?? localStorage;

export function useStored<T>(key: string, initial: T, valid: (value: unknown) => value is T) {
  const [value, setValue] = useState(initial);
  const [restored, setRestored] = useState(false);
  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      try {
        const raw = storage().getItem(key);
        const parsed: unknown = raw === null ? null : JSON.parse(raw);
        if (valid(parsed)) setValue(parsed);
      } catch {
        /* Unavailable storage or an older corrupt cache must not block reading. */
      }
      setRestored(true);
    });
    return () => {
      cancelled = true;
    };
  }, [key, valid]);
  useEffect(() => {
    if (!restored) return;
    try {
      storage().setItem(key, JSON.stringify(value));
    } catch {
      /* In-memory reading still works. */
    }
  }, [key, restored, value]);
  return [value, setValue, restored] as const;
}
