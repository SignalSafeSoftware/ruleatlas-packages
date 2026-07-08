import {
  DiscoveryMetricsTable,
  type MetricsTableColumn,
  type MetricsTableExpandable,
  type MetricsTableFooterContext,
  type MetricsTableFooterSpec,
  type MetricsTableScopeOption,
  type SortDirection,
  type TieBreaker,
} from './DiscoveryMetricsTable';

export type LineCountByFileTypeTableProps<T extends Record<string, unknown>> = {
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
};

export function LineCountByFileTypeTable<T extends Record<string, unknown>>(
  props: LineCountByFileTypeTableProps<T>,
): React.ReactElement {
  return <DiscoveryMetricsTable {...props} />;
}
