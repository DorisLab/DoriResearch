import { fromHost, send } from './bridge';
import type { PublicationPage, PublicationQuery } from '../types';
import { trackViewRequest } from '../viewCheckpoint';

export function queryPublications(request: PublicationQuery): Promise<PublicationPage> {
  const finish = trackViewRequest();
  return new Promise<PublicationPage>((resolve, reject) => {
    const requestId = crypto.randomUUID();
    const cleanup = () => {
      window.clearTimeout(timer);
      window.removeEventListener('message', listener);
    };
    const listener = (event: MessageEvent) => {
      if (
        !fromHost(event) ||
        event.data.type !== 'publication-page' ||
        event.data.payload?.requestId !== requestId
      )
        return;
      cleanup();
      const { result, error } = event.data.payload;
      if (error) reject(new Error(error));
      else resolve(result);
    };
    const timer = window.setTimeout(() => {
      cleanup();
      reject(new Error('读取超时，请重试'));
    }, 15000);
    window.addEventListener('message', listener);
    send('query-publications', { requestId, request });
  }).finally(finish);
}
