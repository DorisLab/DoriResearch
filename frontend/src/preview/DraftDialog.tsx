import * as Dialog from '@radix-ui/react-dialog';
import { X, Plus } from '@phosphor-icons/react';
import type { Dispatch, SetStateAction } from 'react';
import type { Reference } from '../types';
import type { Drafts } from './state';

interface Props {
  open: boolean;
  onOpenChange: (value: boolean) => void;
  drafts: Drafts;
  setDrafts: Dispatch<SetStateAction<Drafts>>;
}
export function DraftDialog({ open, onOpenChange, drafts, setDrafts }: Props) {
  const draft = drafts.items.find((item) => item.id === drafts.active);
  function setText(text: string) {
    setDrafts((current) => ({
      ...current,
      items: current.items.map((item) => (item.id === current.active ? { ...item, text } : item)),
    }));
  }
  function newDraft() {
    if (!draft) return;
    const next = { id: crypto.randomUUID(), sourceKey: draft.sourceKey, text: '', references: [] };
    setDrafts((current) => ({ active: next.id, items: [...current.items, next] }));
  }
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="draft-dialog">
          <div className="dialog-title-row">
            <Dialog.Title>讨论草稿</Dialog.Title>
            <Dialog.Close className="icon-button" aria-label="关闭草稿">
              <X />
            </Dialog.Close>
          </div>
          <Dialog.Description>
            开发预览：引用和文字保存在此浏览器，尚未发送给 Dorislab Agent。
          </Dialog.Description>
          <div className="draft-toolbar">
            <label>
              草稿
              <select
                aria-label="切换讨论草稿"
                value={drafts.active}
                onChange={(event) => {
                  const active = event.target.value;
                  setDrafts((current) => ({ ...current, active }));
                }}
              >
                {drafts.items.map((item, index) => (
                  <option key={item.id} value={item.id}>
                    草稿 {index + 1} · {item.references[0]?.source.title ?? '未添加引用'}
                  </option>
                ))}
              </select>
            </label>
            <button className="quiet" onClick={newDraft}>
              <Plus />
              新草稿
            </button>
          </div>
          {draft && (
            <>
              <ReferenceList references={draft.references} />
              <textarea
                aria-label="讨论内容"
                placeholder="接下来想研究什么？"
                value={draft.text}
                onChange={(event) => setText(event.target.value)}
                rows={4}
              />
            </>
          )}
          <div className="draft-footer">
            <span>草稿自动保留</span>
            <Dialog.Close className="primary">保存并返回</Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ReferenceList({ references }: { references: Reference[] }) {
  return (
    <div className="reference-list">
      {references.map((reference, index) => (
        <article key={`${reference.createdAt}:${index}`} className="reference-card">
          <div className="eyebrow">
            {reference.kind === 'text'
              ? '文字引用'
              : reference.kind === 'chart'
                ? '图表引用'
                : '成果引用'}{' '}
            · {reference.source.title}
          </div>
          <blockquote>{reference.quote}</blockquote>
          <details>
            <summary>查看冻结内容</summary>
            <pre>{JSON.stringify(reference, null, 2)}</pre>
          </details>
        </article>
      ))}
    </div>
  );
}
