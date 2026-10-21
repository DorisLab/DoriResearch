import { useEffect, useMemo, useState } from 'react';
import { useStored } from './storage';
import { keyOf, type ResearchHost } from './types';
import { Studio } from './Studio';
import { PublishedPage } from './pages/PublishedPage';
import type { PublicationContent, PublicationSummary } from './publicationContracts';
import { DraftDialog } from './preview/DraftDialog';
import { Tabs } from './preview/Tabs';
import {
  attachReference,
  closeTab,
  initialDrafts,
  initialTabs,
  isDrafts,
  isTabs,
  openTab,
} from './preview/state';

export function App() {
  const [tabs, setTabs] = useStored('doriresearch.library.preview.tabs.v1', initialTabs, isTabs);
  const [drafts, setDrafts] = useStored(
    'dorislab.research.preview.drafts.v2',
    initialDrafts,
    isDrafts,
  );
  const [draftOpen, setDraftOpen] = useState(false);
  const target = tabs.items.find((item) => keyOf(item) === tabs.active);
  const { publications, content, error } = usePreviewContent(target);
  const host = useMemo<ResearchHost>(
    () => ({
      protocolVersion: 1,
      request: rpc,
      queryPublications: (query) => rpc('page', { ...query }),
      readFile: (path) => rpc('text', { reference: target, path }),
      readImage: async (path) => {
        const file = await rpc<{ mime: string; bytes: string }>('file', {
          reference: target,
          path,
        });
        return `data:${file.mime};base64,${file.bytes}`;
      },
      open: (target) => setTabs((current) => openTab(current, target)),
      reference: (reference) => {
        setDrafts((current) => attachReference(current, reference, crypto.randomUUID()));
        setDraftOpen(true);
      },
    }),
    [target, setTabs, setDrafts],
  );
  return (
    <div className="preview-app" onContextMenu={(event) => event.preventDefault()}>
      <div className="preview-context">
        <strong>Dorislab</strong>
        <span>研究工程 · 开发预览</span>
        <span className="preview-scope">独立测试数据库</span>
      </div>
      <Tabs
        state={tabs}
        select={(active) => setTabs((current) => ({ ...current, active }))}
        close={(key) => setTabs((current) => closeTab(current, key))}
        drafts={() => setDraftOpen(true)}
      />
      <div className="studio-slot" hidden={!!target}>
        <Studio host={host} publications={publications} />
      </div>
      {error && <p role="alert">{error}</p>}
      {target &&
        content &&
        keyOf(target) === keyOf({ ...content.item.reference, title: content.item.title }) && (
          <div className="artifact-scroll">
            <PublishedPage content={content} host={host} />
          </div>
        )}
      <DraftDialog
        open={draftOpen}
        onOpenChange={setDraftOpen}
        drafts={drafts}
        setDrafts={setDrafts}
      />
    </div>
  );
}

async function rpc<T>(operation: string, args: Record<string, unknown>): Promise<T> {
  const response = await fetch('/research-api', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operation, args }),
  });
  if (!response.ok) throw new Error('请通过 scripts/dev.py 启动研究服务和前端');
  const value = await response.json();
  if (value.error) throw new Error(value.error);
  return value.result;
}

function usePreviewContent(target: import('./types').Target | undefined) {
  const [publications, setPublications] = useState<PublicationSummary[]>([]);
  const [content, setContent] = useState<PublicationContent>();
  const [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    void Promise.all([
      rpc<PublicationSummary[]>('list', {}),
      target ? rpc<PublicationContent>('content', { reference: target }) : undefined,
    ])
      .then(([items, page]) => {
        if (current) {
          setPublications(items);
          setContent(page);
          setError('');
        }
      })
      .catch((reason: unknown) => {
        if (current) setError(String(reason));
      });
    return () => {
      current = false;
    };
  }, [target]);
  return { publications, content, error };
}
