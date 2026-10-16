import { createContext, useContext } from 'react';
import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { PublicationContent } from '../publicationContracts';
import type { ResearchHost } from '../types';
import { PublishedImage } from './PublishedImage';
import { ContentBlock } from '../components/ContentBlock';
import '../styles/content-blocks.css';

type Source = { content: PublicationContent; host: ResearchHost };
const SourceContext = createContext<Source | null>(null);
function useSource() {
  const source = useContext(SourceContext);
  if (!source) throw new Error('研究正文缺少读取上下文');
  return source;
}

// Stable component types keep loaded images mounted during host/list updates.
const components: Components = {
  h1: function Heading({ children }) {
    const { content } = useSource();
    return children === content.item.title ? null : <h2>{children}</h2>;
  },
  a: function Link({ href, children }) {
    const { content, host } = useSource();
    return content.files.some((file) => file.path === href) ? (
      <button className="text-link" onClick={() => host.previewFile?.(href!)}>
        {children}
      </button>
    ) : (
      <span>{children}</span>
    );
  },
  img: function Image({ src, alt }) {
    const { content, host } = useSource();
    return typeof src === 'string' && content.files.some((file) => file.path === src) ? (
      <PublishedImage path={src} alt={alt} host={host} />
    ) : (
      <span>{alt}</span>
    );
  },
  table: ({ children }) => (
    <div className="table-scroll" role="region" aria-label="研究数据表" tabIndex={0}>
      <table>{children}</table>
    </div>
  ),
  pre: function Code({ children, node }) {
    const { content, host } = useSource();
    const code = node?.children[0];
    if (code?.type === 'element' && code.tagName === 'code') {
      const language = String(code.properties.className ?? '').replace('language-', '');
      const value = code.children
        .map((child) => (child.type === 'text' ? child.value : ''))
        .join('');
      if (['echarts', 'metrics', 'datatable'].includes(language))
        return (
          <ContentBlock
            title={content.item.title}
            kind={language}
            value={value}
            reference={content.item.reference}
            host={host}
          />
        );
    }
    return (
      <pre className="code-scroll" tabIndex={0}>
        {children}
      </pre>
    );
  },
};
const plugins = [remarkGfm];

export function PublishedMarkdown(source: Source) {
  return (
    <SourceContext.Provider value={source}>
      <Markdown remarkPlugins={plugins} components={components}>
        {source.content.body}
      </Markdown>
    </SourceContext.Provider>
  );
}
