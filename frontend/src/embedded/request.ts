import { fromHost, send } from './bridge';
import { trackViewRequest } from '../viewCheckpoint';

export function request<T>(operation: string, args: Record<string, unknown>): Promise<T> {
  const finish = trackViewRequest();
  return new Promise<T>((resolve, reject) => {
    const requestId = crypto.randomUUID();
    const cleanup = () => {
      clearTimeout(timer);
      window.removeEventListener('message', listener);
    };
    const listener = (event: MessageEvent) => {
      if (
        !fromHost(event) ||
        event.data.type !== 'research-response' ||
        event.data.payload?.requestId !== requestId
      )
        return;
      cleanup();
      const { error, result } = event.data.payload;
      if (error) reject(new Error(error));
      else resolve(result);
    };
    const timer = window.setTimeout(() => {
      cleanup();
      reject(new Error('研究服务请求超时，请重试'));
    }, 35000);
    window.addEventListener('message', listener);
    send('research-request', { requestId, operation, args });
  }).finally(finish);
}
