import { ResearchIcon } from '../components/ResearchIcon';
import { ChatCircleDots, X } from '@phosphor-icons/react';
import { keyOf } from '../types';
import type { Tabs as TabState } from './state';

export function Tabs({
  state,
  select,
  close,
  drafts,
}: {
  state: TabState;
  select: (key: string) => void;
  close: (key: string) => void;
  drafts: () => void;
}) {
  return (
    <div className="preview-tabbar">
      <nav aria-label="内容标签">
        <button
          className={`content-tab ${state.active === 'studio' ? 'active' : ''}`}
          onClick={() => select('studio')}
        >
          <ResearchIcon kind="research-room" />
          我的研究室
        </button>
        {state.items.map((target) => (
          <div
            className={`content-tab ${state.active === keyOf(target) ? 'active' : ''}`}
            key={keyOf(target)}
          >
            <button onClick={() => select(keyOf(target))}>
              <ResearchIcon kind={target.kind} />
              {target.title}
            </button>
            <button
              className="close-tab"
              aria-label={`关闭 ${target.title}`}
              onClick={() => close(keyOf(target))}
            >
              <X />
            </button>
          </div>
        ))}
      </nav>
      <button className="icon-button" aria-label="打开讨论草稿" onClick={drafts}>
        <ChatCircleDots />
      </button>
    </div>
  );
}
