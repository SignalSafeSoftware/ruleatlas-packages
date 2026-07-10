import { formatInteger } from '../utils/numberFormat';
import type {
  MetricsTableColumn,
  SortDirection,
  TieBreaker,
} from './discoveryMetricsTableTypes';

export function formatCellValue<T extends Record<string, unknown>>(
  raw: unknown,
  column: MetricsTableColumn<T>,
  row: T,
): string {
  if (column.format) {
    return column.format(raw, row);
  }
  if (raw === null || raw === undefined) {
    return '—';
  }
  const useNumeric = column.numeric ?? column.align === 'end';
  if (useNumeric && typeof raw === 'number' && Number.isFinite(raw)) {
    return formatInteger(raw);
  }
  if (typeof raw === 'string') {
    return raw;
  }
  if (typeof raw === 'number' || typeof raw === 'boolean' || typeof raw === 'bigint') {
    return raw.toString();
  }
  return '—';
}

export function metricsSortAriaValue(
  isActive: boolean,
  direction: SortDirection,
): 'ascending' | 'descending' | undefined {
  if (!isActive) return undefined;
  return direction === 'asc' ? 'ascending' : 'descending';
}

function compareValues(a: number | string, b: number | string, direction: SortDirection): number {
  const factor = direction === 'asc' ? 1 : -1;
  if (typeof a === 'number' && typeof b === 'number') {
    return (a - b) * factor;
  }
  return String(a).localeCompare(String(b), undefined, { sensitivity: 'base' }) * factor;
}

function resolveSortValue<T extends Record<string, unknown>>(
  col: MetricsTableColumn<T>,
  row: T,
  override?: (row: T) => number | string,
): number | string {
  if (override) return override(row);
  if (col.sortValue) return col.sortValue(row);
  const raw = row[col.key];
  if (typeof raw === 'number') return raw;
  return String(raw ?? '');
}

export function sortAndFilterMetricsRows<T extends Record<string, unknown>>(options: {
  rows: T[];
  columns: MetricsTableColumn<T>[];
  filterText: string;
  filterFn?: (row: T, query: string) => boolean;
  sortColumnId: string;
  sortDirection: SortDirection;
  tieBreakers?: TieBreaker<T>[];
}): T[] {
  const query = options.filterText.trim().toLowerCase();
  let next = options.rows;
  if (query && options.filterFn) {
    next = next.filter((row) => options.filterFn!(row, query));
  }
  const column =
    options.columns.find((item) => item.id === options.sortColumnId) ?? options.columns[0];
  if (!column || column.sortable === false) {
    return next;
  }
  const getValue =
    column.sortValue ??
    ((row: T) => {
      const raw = row[column.key];
      if (typeof raw === 'number') return raw;
      return String(raw ?? '');
    });
  return [...next].sort((left, right) => {
    const primary = compareValues(getValue(left), getValue(right), options.sortDirection);
    if (primary !== 0) return primary;
    for (const breaker of options.tieBreakers ?? []) {
      const breakerColumn = options.columns.find((item) => item.id === breaker.columnId);
      if (!breakerColumn) continue;
      const leftValue = resolveSortValue(breakerColumn, left, breaker.sortValue);
      const rightValue = resolveSortValue(breakerColumn, right, breaker.sortValue);
      const tie = compareValues(leftValue, rightValue, breaker.direction);
      if (tie !== 0) return tie;
    }
    return 0;
  });
}
