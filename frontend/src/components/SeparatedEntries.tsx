import { Children, Fragment, type ReactNode } from 'react';
import { Divider } from '../../ui/Divider';

export function SeparatedEntries({
  children,
  className,
}: {
  children: ReactNode;
  className: string;
}) {
  return (
    <div className={className}>
      {Children.toArray(children).map((child, index) => (
        <Fragment key={typeof child === 'object' && 'key' in child ? child.key : index}>
          {index > 0 && <Divider />}
          {child}
        </Fragment>
      ))}
    </div>
  );
}
