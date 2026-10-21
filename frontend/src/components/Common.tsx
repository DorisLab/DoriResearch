import { ResearchIcon } from './ResearchIcon';
import { ArrowUpRight, ChatCircleDots, DownloadSimple } from '@phosphor-icons/react';
import type { ReactNode } from 'react';
import { hostDownload } from './download';
import { objectReference, type ResearchHost, type Target } from '../types';
import { PublicationMore } from '../../ui/PublicationMore';

export function OpenLink({
  target,
  host,
  children,
}: {
  target: Target;
  host: ResearchHost;
  children?: ReactNode;
}) {
  return (
    <button className="text-link" onClick={() => host.open(target)}>
      {children ?? target.title}
      <ArrowUpRight />
    </button>
  );
}
export function PageHeader({
  target,
  host,
  label,
  summary,
}: {
  target: Target;
  host: ResearchHost;
  label?: string;
  summary?: string;
}) {
  return (
    <header className="page-header">
      {(label || host.publicationActions?.archived) && (
        <div className="eyebrow">
          {label}
          {host.publicationActions?.archived && <span>已归档</span>}
        </div>
      )}
      <div className="heading-row">
        <h1>
          <ResearchIcon kind={target.kind} />
          {target.title}
        </h1>
        <div className="report-actions">
          <button className="primary" onClick={() => host.reference(objectReference(target))}>
            <ChatCircleDots />
            继续讨论
          </button>
          {host.publicationActions && <PublicationMore {...host.publicationActions} />}
        </div>
      </div>
      {summary && <p className="lede">{summary}</p>}
    </header>
  );
}
export function Download({ path, children }: { path: string; children: ReactNode }) {
  return (
    <button className="text-link" onClick={() => hostDownload(path)}>
      <DownloadSimple />
      {children}
    </button>
  );
}
