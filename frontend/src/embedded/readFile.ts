import { fromHost, send } from './bridge';
import type { PublicationRef } from '../publicationContracts';

let queue: Promise<unknown> = Promise.resolve();
export function readFile(
  path: string,
  image = false,
  cover?: PublicationRef,
  listed?: PublicationRef,
): Promise<string> {
  const result = queue.then(() => requestFile(path, image, cover, listed));
  queue = result.catch(() => {});
  return result;
}
function requestFile(
  path: string,
  image: boolean,
  cover?: PublicationRef,
  listed?: PublicationRef,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const requestId = crypto.randomUUID();
    const cleanup = () => {
      window.clearTimeout(timer);
      window.removeEventListener('message', listener);
    };
    const listener = (event: MessageEvent) => {
      if (
        !fromHost(event) ||
        event.data.type !== 'file' ||
        event.data.payload?.requestId !== requestId
      )
        return;
      cleanup();
      const { text, error } = event.data.payload;
      if (typeof text === 'string') resolve(text);
      else reject(new Error(typeof error === 'string' ? error : '成果文件读取失败'));
    };
    const timer = window.setTimeout(() => {
      cleanup();
      reject(new Error('成果文件读取超时，请重试'));
    }, 15000);
    window.addEventListener('message', listener);
    send('read-file', { requestId, path, image, cover, listed });
  });
}
