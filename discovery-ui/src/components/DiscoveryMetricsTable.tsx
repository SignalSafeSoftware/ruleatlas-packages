import { Fragment, useMemo, useState } from 'react';
import {
  formatCellValue,
  metricsSortAriaValue,
  sortAndFilterMetricsRows,
} from './discoveryMetricsTableHelpers';
import type {
  MetricsTableColumn,
  MetricsTableExpandable,
  MetricsTableFooterContext,
  MetricsTableFooterSpec,
  MetricsTableScopeOption,
  SortDirection,
  TieBreaker,
} from './discoveryMetricsTableTypes';

export type {
  MetricsTableColumn,
  MetricsTableExpandable,
  MetricsTableFooterContext,
  MetricsTableFooterSpec,
  MetricsTableScopeOption,
  SortDirection,
  TieBreaker,
} from './discoveryMetricsTableTypes';

function MetricsTableToolbar<T extends Record<string, unknown>>({
  testId,
  filterPlaceholder,
  filterText,
  onFilterChange,
  scopeFilter,
}: Readonly<{
  testId: string;
  filterPlaceholder?: string;
  filterText: string;
  onFilterChange: (value: string) => void;
  scopeFilter?: {
    label?: string;
    value: string;
    options: MetricsTableScopeOption[];
    onChange: (value: string) => void;
    testId?: string;
    helpText?: string;
  };
}>): React.ReactElement | null {
  if (!filterPlaceholder && !scopeFilter) return null;
  return (
    <div className="row g-2 mb-3">
      {filterPlaceholder ? (
        <div className={scopeFilter ? 'col-md-8' : 'col-12'}>
          <input
            type="search"
            className="form-control form-control-sm"
            placeholder={filterPlaceholder}
            value={filterText}
            onChange={(event) => onFilterChange(event.target.value)}
            data-testid={`${testId}-filter`}
            aria-label={filterPlaceholder}
          />
        </div>
      ) : null}
      {scopeFilter ? (
        <div className={filterPlaceholder ? 'col-md-4' : 'col-12 col-md-6 col-lg-4'}>
          <label className="visually-hidden" htmlFor={`${testId}-scope`}>
            {scopeFilter.label ?? 'Scope'}
          </label>
          <select
            id={`${testId}-scope`}
            className="form-select form-select-sm"
            value={scopeFilter.value}
            onChange={(event) => scopeFilter.onChange(event.target.value)}
            data-testid={scopeFilter.testId ?? `${testId}-scope`}
          >
            {scopeFilter.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </div>
  );
}

function MetricsTableBody<T extends Record<string, unknown>>({
  columns,
  rows,
  testId,
  sortColumnId,
  sortDirection,
  onToggleSort,
  expandable,
  footerSpec,
}: Readonly<{
  columns: MetricsTableColumn<T>[];
  rows: T[];
  testId: string;
  sortColumnId: string;
  sortDirection: SortDirection;
  onToggleSort: (column: MetricsTableColumn<T>) => void;
  expandable?: MetricsTableExpandable<T>;
  footerSpec: MetricsTableFooterSpec | null;
}>): React.ReactElement {
  function sortIndicator(columnId: string): string {
    if (sortColumnId !== columnId) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  }

  return (
    <div className="table-responsive">
      <table className="table table-sm table-striped table-hover ruleatlas-table mb-0">
        <thead>
          <tr>
            {columns.map((column) => {
              const sortable = column.sortable !== false;
              return (
                <th
                  key={column.id}
                  className={column.align === 'end' ? 'text-end' : undefined}
                  aria-sort={metricsSortAriaValue(sortColumnId === column.id, sortDirection)}
                >
                  {sortable ? (
                    <button
                      type="button"
                      className={`btn btn-link btn-sm p-0 text-decoration-none ${
                        column.align === 'end' ? 'float-end' : ''
                      }`}
                      onClick={() => onToggleSort(column)}
                      data-testid={`${testId}-sort-${column.id}`}
                    >
                      {column.label}
                      {sortIndicator(column.id)}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-body-secondary small">
                No rows match the current filter.
              </td>
            </tr>
          ) : (
            rows.map((row, index) => {
              const rowKey = expandable?.rowKey(row) ?? `${String(row[columns[0]?.key ?? 'key'])}-${index}`;
              const isExpanded = expandable?.expandedKeys.has(rowKey) ?? false;
              const canExpand = expandable?.canExpand?.(row) ?? true;
              return (
                <Fragment key={rowKey}>
                  <tr>
                    {columns.map((column) => {
                      const raw = row[column.key];
                      return (
                        <td key={column.id} className={column.align === 'end' ? 'text-end' : undefined}>
                          {column.render ? column.render(row) : formatCellValue(raw, column, row)}
                        </td>
                      );
                    })}
                  </tr>
                  {expandable && isExpanded && canExpand ? (
                    <tr key={`${rowKey}-expanded`} className="discovery-expanded-row">
                      <td colSpan={columns.length} className="p-0">
                        {expandable.renderExpanded(row)}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })
          )}
        </tbody>
        {footerSpec ? (
          <tfoot className="discovery-table-footer">
            <tr data-testid={`${testId}-footer`}>
              {columns.map((column) => {
                const labelColumnId = footerSpec.labelColumnId ?? columns[0]?.id;
                const cell =
                  footerSpec.cells[column.id] ??
                  (column.id === labelColumnId ? footerSpec.label : null);
                return (
                  <td
                    key={column.id}
                    className={column.align === 'end' ? 'text-end' : undefined}
                    data-testid={
                      column.id === labelColumnId ? `${testId}-footer-label` : `${testId}-footer-${column.id}`
                    }
                  >
                    {cell}
                  </td>
                );
              })}
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}

export function DiscoveryMetricsTable<T extends Record<string, unknown>>({
  title,
  description,
  testId,
  columns,
  rows,
  emptyLabel = 'No data',
  defaultSort,
  filterPlaceholder,
  filterFn,
  scopeFilter,
  tieBreakers,
  footerRow,
  tableNote,
  fillHeight = false,
  expandable,
}: Readonly<{
  title: string;
  description?: string;
  testId: string;
  columns: MetricsTableColumn<T>[];
  rows: T[];
  emptyLabel?: string;
  defaultSort?: { columnId: string; direction: SortDirection };
  filterPlaceholder?: string;
  filterFn?: (row: T, query: string) => boolean;
  scopeFilter?: {
    label?: string;
    value: string;
    options: MetricsTableScopeOption[];
    onChange: (value: string) => void;
    testId?: string;
    helpText?: string;
  };
  tieBreakers?: TieBreaker<T>[];
  footerRow?: MetricsTableFooterSpec | ((ctx: MetricsTableFooterContext<T>) => MetricsTableFooterSpec);
  tableNote?: React.ReactNode;
  fillHeight?: boolean;
  expandable?: MetricsTableExpandable<T>;
}>): React.ReactElement {
  const [sortColumnId, setSortColumnId] = useState(defaultSort?.columnId ?? columns[0]?.id ?? '');
  const [sortDirection, setSortDirection] = useState<SortDirection>(defaultSort?.direction ?? 'desc');
  const [filterText, setFilterText] = useState('');

  const sortedFilteredRows = useMemo(
    () =>
      sortAndFilterMetricsRows({
        rows,
        columns,
        filterText,
        filterFn,
        sortColumnId,
        sortDirection,
        tieBreakers,
      }),
    [columns, filterFn, filterText, rows, sortColumnId, sortDirection, tieBreakers],
  );

  const filterActive = filterText.trim().length > 0;
  const footerSpec = useMemo(() => {
    if (!footerRow || rows.length === 0) return null;
    const ctx: MetricsTableFooterContext<T> = {
      filteredRows: sortedFilteredRows,
      allRows: rows,
      filterActive,
    };
    return typeof footerRow === 'function' ? footerRow(ctx) : footerRow;
  }, [footerRow, filterActive, rows, sortedFilteredRows]);

  function toggleSort(column: MetricsTableColumn<T>): void {
    if (column.sortable === false) return;
    if (sortColumnId === column.id) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortColumnId(column.id);
    setSortDirection(column.align === 'end' ? 'desc' : 'asc');
  }

  return (
    <div className={fillHeight ? 'h-100' : undefined} data-testid={testId}>
      <h3 className="h6 mb-1">{title}</h3>
      {description ? <p className="small text-body-secondary mb-2">{description}</p> : null}
      {scopeFilter?.helpText ? (
        <p className="small text-body-secondary mb-2" data-testid={`${testId}-scope-help`}>
          {scopeFilter.helpText}
        </p>
      ) : null}
      <MetricsTableToolbar
        testId={testId}
        filterPlaceholder={filterPlaceholder}
        filterText={filterText}
        onFilterChange={setFilterText}
        scopeFilter={scopeFilter}
      />
      {rows.length === 0 ? (
        <p className="text-body-secondary small mb-0">{emptyLabel}</p>
      ) : (
        <MetricsTableBody
          columns={columns}
          rows={sortedFilteredRows}
          testId={testId}
          sortColumnId={sortColumnId}
          sortDirection={sortDirection}
          onToggleSort={toggleSort}
          expandable={expandable}
          footerSpec={footerSpec}
        />
      )}
      {tableNote ? <div className="mt-3">{tableNote}</div> : null}
    </div>
  );
}

export { formatPercent } from '../utils/numberFormat';

export const BUCKET_LABELS: Record<string, string> = {
  production: 'Production',
  tests: 'Tests',
  docs: 'Docs',
  config: 'Config',
  generated_or_vendor: 'Generated/vendor',
  artifacts: 'Artifacts',
  unknown: 'Unknown',
};

export function bucketLabel(bucket: string): string {
  return BUCKET_LABELS[bucket] ?? bucket;
}
