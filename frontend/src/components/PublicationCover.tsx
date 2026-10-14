import * as Dialog from '@radix-ui/react-dialog';
import { useEffect, useRef, useState } from 'react';
import type { PublicationSummary } from '../publicationContracts';
import type { ResearchHost } from '../types';

export function PublicationCover({ item, host }: { item: PublicationSummary; host: ResearchHost }) {
  const element = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined');
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ url?: string; error?: string }>({});
  useEffect(() => {
    if (!element.current || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '150px' },
    );
    observer.observe(element.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible || !item.cover || !host.readCover) return;
    let current = true;
    void host.readCover(item.reference, item.cover).then(
      (url) => {
        if (current) setResult({ url });
      },
      () => {
        if (current) setResult({ error: '封面暂不可用' });
      },
    );
    return () => {
      current = false;
    };
  }, [visible, item.cover, item.reference, host, attempt]);
  return (
    <figure ref={element} className="study-cover publication-cover">
      {result.url ? (
        <Dialog.Root>
          <Dialog.Trigger asChild>
            <button className="cover-preview" aria-label={`查看${item.title}配图`}>
              <img
                src={result.url}
                alt={`${item.title}配图`}
                onError={() => setResult({ error: '封面无法显示' })}
              />
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="cover-overlay" />
            <Dialog.Content className="cover-dialog" aria-describedby={undefined}>
              <Dialog.Title>{item.title}</Dialog.Title>
              <img src={result.url} alt={`${item.title}配图`} />
              <Dialog.Close className="quiet">关闭</Dialog.Close>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      ) : result.error ? (
        <div>
          <p>{result.error}</p>
          <button
            onClick={() => {
              setResult({});
              setAttempt((v) => v + 1);
            }}
          >
            重试
          </button>
        </div>
      ) : (
        <span className="muted">正在读取封面…</span>
      )}
    </figure>
  );
}
