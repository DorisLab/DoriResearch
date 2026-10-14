import * as Menu from '@radix-ui/react-dropdown-menu';
import { DotsThree, Archive, ArrowCounterClockwise } from '@phosphor-icons/react';
import './publication-more.css';

export interface PublicationActions {
  archived: boolean;
  busy: boolean;
  archive(): void;
}
export function PublicationMore({ archived, busy, archive }: PublicationActions) {
  return (
    <Menu.Root>
      <Menu.Trigger className="publication-more" aria-label="更多" disabled={busy}>
        <DotsThree aria-hidden="true" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content
          className="publication-more-menu"
          align="end"
          sideOffset={6}
          collisionPadding={8}
        >
          <Menu.Item onSelect={archive} disabled={busy}>
            {archived ? <ArrowCounterClockwise /> : <Archive />}
            {archived ? '取消归档' : '归档'}
          </Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}
