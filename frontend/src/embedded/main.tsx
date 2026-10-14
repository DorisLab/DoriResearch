import { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { IconContext } from '@phosphor-icons/react';
import { Studio } from '../Studio';
import { PublishedPage } from '../pages/PublishedPage';
import { setResearchStorage } from '../storage';
import { setDownloadHandler } from '../components/download';
import type { ResearchHost } from '../types';
import { applyAppearance, receive, send, type Init } from './bridge';
import { readFile } from './readFile';
import { queryPublications } from './queryPublications';
import '../styles/base.css';
import '../styles/studio.css';
import '../styles/report.css';
import '../styles/typography.css';
import '../styles/bundled-fonts.css';
import './style.css';

const host: ResearchHost = {
  protocolVersion: 1,
  previewFile: (path) => send('preview-file', path),
  queryPublications,
  open: (target) => send('open', target),
  reference: (reference) => send('reference', reference),
  readFile,
  readPublicationFile: (reference, path) => readFile(path, false, undefined, reference),
  readImage: (path) => readFile(path, true),
  readCover: (reference, path) => readFile(path, true, reference),
};
setDownloadHandler((path) => send('download', path));

function EmbeddedResearch() {
  const [init, setInit] = useState<Init | null>(null);
  const actions = init?.lifecycle;
  const publicationHost = useMemo(
    () => ({
      ...host,
      publicationActions: actions ? { ...actions, archive: () => send('archive') } : undefined,
    }),
    [actions],
  );
  useEffect(() => {
    const unsubscribe = receive((type, payload) => {
      if (type === 'hello') {
        send('ready', { capabilities: ['publication-reader-v1'] });
        return;
      }
      if (type === 'appearance') {
        applyAppearance(payload.appearance);
        return;
      }
      if (type === 'lifecycle') {
        setInit((current) =>
          current &&
          (current.lifecycle?.archived !== payload.lifecycle?.archived ||
            current.lifecycle?.busy !== payload.lifecycle?.busy)
            ? { ...current, lifecycle: payload.lifecycle }
            : current,
        );
        return;
      }
      if (type === 'publications') {
        setInit((current) =>
          current && !current.target ? { ...current, publications: payload.publications } : current,
        );
        return;
      }
      if (type !== 'init') return;
      applyAppearance(payload.appearance);
      const cache = { ...payload.storage };
      setResearchStorage({
        getItem: (key) => cache[key] ?? null,
        setItem: (key, value) => {
          cache[key] = value;
          send('storage', { key, value });
        },
      });
      setInit(payload);
    });
    send('ready', { capabilities: ['publication-reader-v1'] });
    return unsubscribe;
  }, []);
  if (!init)
    return (
      <div className="empty" role="status">
        正在读取研究内容…
      </div>
    );
  return init.target ? (
    <div className="artifact-scroll">
      {init.publication ? (
        <PublishedPage content={init.publication} host={publicationHost} />
      ) : (
        <p className="empty">这个成果暂不可用。</p>
      )}
    </div>
  ) : (
    <Studio host={host} publications={init.publications} />
  );
}
createRoot(document.getElementById('root')!).render(
  <IconContext.Provider value={{ weight: 'light', className: 'research-icon' }}>
    <EmbeddedResearch />
  </IconContext.Provider>,
);
