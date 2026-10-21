import type { ReactNode } from 'react';
import type { ResearchHost, Target } from '../types';
import { ReadingRegion } from '../../ui/ReadingRegion';

export function TextSelection({
  source,
  host,
  children,
}: {
  source: Target;
  host: ResearchHost;
  children: ReactNode;
}) {
  return (
    <ReadingRegion
      reference={({ text, range }) => {
        const node =
          range.startContainer.nodeType === Node.ELEMENT_NODE
            ? (range.startContainer as Element)
            : range.startContainer.parentElement;
        host.reference({
          schemaVersion: 1,
          source,
          kind: 'text',
          locator: node?.closest('section')?.id ?? 'body',
          quote: text,
          createdAt: new Date().toISOString(),
        });
      }}
    >
      {children}
    </ReadingRegion>
  );
}
