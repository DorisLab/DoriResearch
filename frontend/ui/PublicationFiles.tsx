import { useEffect, useRef, useState } from 'react';
import { CaretDown } from '@phosphor-icons/react';
import './publication-files.css';

export function PublicationFiles({
  files,
  open,
}: {
  files: { path: string }[];
  open(path: string): void;
}) {
  const [expanded, setExpanded] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = list.current;
    if (!expanded || !element) return;
    const refresh = () => {
      element.toggleAttribute('data-above', element.scrollTop > 1);
      element.toggleAttribute(
        'data-below',
        element.scrollHeight - element.clientHeight - element.scrollTop > 1,
      );
    };
    const observer = new ResizeObserver(refresh);
    observer.observe(element);
    if (element.firstElementChild) observer.observe(element.firstElementChild);
    element.addEventListener('scroll', refresh, { passive: true });
    refresh();
    return () => {
      observer.disconnect();
      element.removeEventListener('scroll', refresh);
    };
  }, [expanded, files]);
  return (
    <details
      className="publication-files"
      onToggle={(event) => setExpanded(event.currentTarget.open)}
    >
      <summary>
        <CaretDown aria-hidden="true" />
        研究文件<span>{files.length}</span>
      </summary>
      {expanded && (
        <div
          ref={list}
          className="publication-files-scroll"
          role="region"
          aria-label="研究文件"
          tabIndex={0}
        >
          <div>
            {files.map((file) => {
              const separator = file.path.lastIndexOf('/') + 1;
              return (
                <button key={file.path} title={file.path} onClick={() => open(file.path)}>
                  {separator > 0 && <span>{file.path.slice(0, separator)}</span>}
                  {file.path.slice(separator)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </details>
  );
}
