export type SortDirection = 'asc' | 'desc';

export type MetricsTableColumn<T extends Record<string, unknown>> = {
  id: string;
  key: keyof T & string;
  label: string;
  align?: 'start' | 'end';
  format?: (value: unknown, row: T) => string;
  render?: (row: T) => React.ReactNode;
  numeric?: boolean;
  sortable?: boolean;
  sortValue?: (row: T) => number | string;
};

export type TieBreaker<T extends Record<string, unknown>> = {
  columnId: string;
  direction: SortDirection;
  sortValue?: (row: T) => number | string;
};

export type MetricsTableFooterContext<T extends Record<string, unknown>> = {
  filteredRows: T[];
  allRows: T[];
  filterActive: boolean;
};

export type MetricsTableFooterSpec = {
  label: string;
  /** First column uses label when no cell is provided for that column id. */
  labelColumnId?: string;
  cells: Partial<Record<string, React.ReactNode>>;
};

export type MetricsTableScopeOption = {
  value: string;
  label: string;
};

export type MetricsTableExpandable<T extends Record<string, unknown>> = {
  expandedKeys: Set<string>;
  rowKey: (row: T) => string;
  onToggle: (key: string) => void;
  canExpand?: (row: T) => boolean;
  renderExpanded: (row: T) => React.ReactNode;
};
