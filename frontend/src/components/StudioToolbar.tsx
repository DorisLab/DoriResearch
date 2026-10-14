import { MagnifyingGlass } from '@phosphor-icons/react';
import { SelectField } from '../../ui/SelectField';
import type { PublicationSummary } from '../publicationContracts';
import type { ListState, Section } from '../studioState';
const labels = { study: '研究', strategy: '策略', run: '运行' };
export function StudioToolbar({
  section,
  view,
  series,
  change,
}: {
  section: Section;
  view: ListState;
  series: PublicationSummary[];
  change(patch: Partial<ListState>): void;
}) {
  return (
    <div className="section-toolbar">
      <label className="studio-search">
        <MagnifyingGlass aria-hidden="true" />
        <input
          type="search"
          aria-label={`搜索${labels[section]}`}
          placeholder={`搜索${labels[section]}`}
          maxLength={120}
          value={view.query}
          onChange={(event) => change({ query: event.target.value })}
        />
      </label>
      <div className="studio-filters">
        {section === 'study' && series.length > 0 && (
          <SelectField
            label="筛选研究系列"
            value={view.series || 'all'}
            options={[
              { value: 'all', label: '全部系列' },
              ...series.map((s) => ({ value: s.reference.id, label: s.title })),
            ]}
            onChange={(value) => change({ series: value === 'all' ? '' : value })}
          />
        )}
        <SelectField
          label="成果排序"
          value={view.sort}
          onChange={(sort) => change({ sort })}
          options={[
            { value: 'newest', label: '最近保存' },
            { value: 'oldest', label: '最早保存' },
            { value: 'title', label: '标题顺序' },
          ]}
        />
      </div>
    </div>
  );
}
export function StudioPagination({
  total,
  page,
  change,
}: {
  total: number;
  page: number;
  change(page: number): void;
}) {
  return (
    <footer className="studio-pagination">
      <span>
        {total
          ? `第 ${(page - 1) * 20 + 1}–${Math.min(page * 20, total)} 项，共 ${total} 项`
          : '共 0 项'}
      </span>
      {total > 20 && (
        <nav aria-label="成果分页">
          <button disabled={page === 1} onClick={() => change(page - 1)}>
            上一页
          </button>
          <span>
            {page} / {Math.ceil(total / 20)}
          </span>
          <button disabled={page * 20 >= total} onClick={() => change(page + 1)}>
            下一页
          </button>
        </nav>
      )}
    </footer>
  );
}
