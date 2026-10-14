import { useState } from 'react';
import { useStored } from './storage';
import { keyOf, type ResearchHost } from './types';
import { Studio } from './Studio';
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
  const [tabs, setTabs] = useStored('dorislab.research.preview.tabs.v1', initialTabs, isTabs);
  const [drafts, setDrafts] = useStored(
    'dorislab.research.preview.drafts.v1',
    initialDrafts,
    isDrafts,
  );
  const [draftOpen, setDraftOpen] = useState(false);
  const host: ResearchHost = {
    protocolVersion: 1,
    open: (target) => setTabs((current) => openTab(current, target)),
    reference: (reference) => {
      setDrafts((current) => attachReference(current, reference, crypto.randomUUID()));
      setDraftOpen(true);
    },
  };
  const target = tabs.items.find((item) => keyOf(item) === tabs.active);
  return (
    <div className="preview-app" onContextMenu={(event) => event.preventDefault()}>
      <div className="preview-context">
        <strong>Dorislab</strong>
        <span>研究工程 · 开发预览</span>
        <span className="preview-scope">未连接客户端成果库</span>
      </div>
      <Tabs
        state={tabs}
        select={(active) => setTabs((current) => ({ ...current, active }))}
        close={(key) => setTabs((current) => closeTab(current, key))}
        drafts={() => setDraftOpen(true)}
      />
      <div className="studio-slot" hidden={!!target}>
        <Studio host={host} />
      </div>
      {target && <p className="empty">请在客户端查看已保存的成果。</p>}
      <DraftDialog
        open={draftOpen}
        onOpenChange={setDraftOpen}
        drafts={drafts}
        setDrafts={setDrafts}
      />
    </div>
  );
}
