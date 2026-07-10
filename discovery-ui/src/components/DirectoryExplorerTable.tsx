import type {
  DirectoryExplorerActions,
  DirectoryExplorerRenderers,
  DiscoveryInventoryFile,
} from '../types/discovery';
import { formatInteger } from '../utils/numberFormat';
import { formatBytes } from '../utils/formatBytes';
import {
  computeDirectoryExplorerTotals,
  sumDirectoryExplorerSubfoldersFooter,
  type DirectorySortColumnId,
  type DirectorySortDirection,
  type FlatDirectoryRow,
} from '../utils/directoryTree';
import { directorySortAriaValue } from '../utils/directoryExplorerHelpers';
import { DirectoryExplorerRow } from './DirectoryExplorerRow';

function formatCount(value: number): string {
  return formatInteger(value);
}

export type DirectoryColumn = {
  id: DirectorySortColumnId | 'actions';
  label: string;
  align?: 'start' | 'end';
  sortable?: boolean;
  headerTitle?: string;
};

export const DIRECTORY_COLUMNS: DirectoryColumn[] = [
  { id: 'name', label: 'Name' },
  { id: 'kind', label: 'Kind' },
  { id: 'classification', label: 'Classification' },
  {
    id: 'folders',
    label: 'Subfolders',
    align: 'end',
    headerTitle:
      'Immediate child folder count for this row. Footer sums Subfolders values for top-level folder rows.',
  },
  { id: 'files', label: 'Files', align: 'end' },
  { id: 'size_bytes', label: 'Size', align: 'end' },
  { id: 'code_lines', label: 'Code', align: 'end' },
  { id: 'comment_lines', label: 'Comments', align: 'end' },
  { id: 'blank_lines', label: 'Blank', align: 'end' },
  { id: 'total_lines', label: 'Total lines', align: 'end' },
  { id: 'actions', label: 'Actions', align: 'end', sortable: false },
];

type DirectoryExplorerToolbarProps = {
  filterText: string;
  onFilterChange: (value: string) => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onExpandTopLevel: () => void;
};

export function DirectoryExplorerToolbar({
  filterText,
  onFilterChange,
  onExpandAll,
  onCollapseAll,
  onExpandTopLevel,
}: Readonly<DirectoryExplorerToolbarProps>): React.ReactElement {
  return (
    <div className="d-flex flex-wrap gap-2 mb-2 align-items-center">
      <input
        className="form-control form-control-sm"
        style={{ maxWidth: '24rem' }}
        placeholder="Inventory keyword search (path, classification, language…)"
        value={filterText}
        onChange={(event) => onFilterChange(event.target.value)}
        data-testid="discovery-directory-explorer-filter"
      />
      <button type="button" className="btn btn-secondary btn-sm" onClick={onExpandAll}>
        Expand all
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onCollapseAll}>
        Collapse all
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onExpandTopLevel}>
        Expand top level
      </button>
    </div>
  );
}

type DirectoryExplorerTableProps = {
  files: DiscoveryInventoryFile[];
  filterText: string;
  filterActive: boolean;
  visibleRows: FlatDirectoryRow[];
  filterEmpty: boolean;
  sortColumnId: DirectorySortColumnId;
  sortDirection: DirectorySortDirection;
  onToggleSort: (column: DirectoryColumn) => void;
  sortIndicator: (columnId: string) => string;
  sourceRootPrefix?: string | null;
  actions: DirectoryExplorerActions;
  renderers: DirectoryExplorerRenderers;
  onToggleExpanded: (id: string, row: FlatDirectoryRow) => void;
};

export function DirectoryExplorerTable({
  files,
  filterText,
  filterActive,
  visibleRows,
  filterEmpty,
  sortColumnId,
  sortDirection,
  onToggleSort,
  sortIndicator,
  sourceRootPrefix,
  actions,
  renderers,
  onToggleExpanded,
}: Readonly<DirectoryExplorerTableProps>): React.ReactElement {
  const footerTotals = computeDirectoryExplorerTotals(files, filterText);
  const subfoldersFooterTotal = sumDirectoryExplorerSubfoldersFooter(visibleRows, { filterActive });

  return (
    <div className="table-responsive">
      <table className="table table-sm table-striped table-hover ruleatlas-table mb-0">
        <thead>
          <tr>
            {DIRECTORY_COLUMNS.map((column) => {
              const sortable = column.sortable !== false && column.id !== 'actions';
              return (
                <th
                  key={column.id}
                  scope="col"
                  className={column.align === 'end' ? 'text-end' : undefined}
                  aria-sort={directorySortAriaValue(
                    sortable,
                    sortColumnId === column.id,
                    sortDirection,
                  )}
                >
                  {sortable ? (
                    <button
                      type="button"
                      className={`btn btn-link btn-sm p-0 text-decoration-none${
                        column.align === 'end' ? ' float-end' : ''
                      }`}
                      onClick={() => onToggleSort(column)}
                      data-testid={`discovery-directory-explorer-sort-${column.id}`}
                      title={
                        column.id === 'name'
                          ? 'Explorer order: hidden folders, visible folders, hidden files, visible files; then name'
                          : column.headerTitle
                      }
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
          {filterEmpty ? (
            <tr>
              <td colSpan={DIRECTORY_COLUMNS.length} className="text-body-secondary small">
                No directories or files match current filter.
              </td>
            </tr>
          ) : (
            visibleRows.map((row) => (
              <DirectoryExplorerRow
                key={row.id}
                row={row}
                sourceRootPrefix={sourceRootPrefix}
                actions={actions}
                renderers={renderers}
                onToggle={() => onToggleExpanded(row.id, row)}
              />
            ))
          )}
        </tbody>
        <tfoot className="discovery-table-footer">
          <tr data-testid="discovery-directory-explorer-footer">
            <td data-testid="discovery-directory-explorer-footer-label">
              {footerTotals.filterActive ? 'Total (filtered)' : 'Total'}
              {!footerTotals.filterActive ? (
                <div className="fw-normal small text-body-secondary">
                  File metrics: all inventoried files. Subfolders: top-level row subtotal.
                </div>
              ) : null}
            </td>
            <td />
            <td />
            <td className="text-end" data-testid="discovery-directory-explorer-footer-folders">
              {formatCount(subfoldersFooterTotal)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-files">
              {formatCount(footerTotals.files)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-size_bytes">
              {formatBytes(footerTotals.sizeBytes)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-code_lines">
              {formatCount(footerTotals.codeLines)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-comment_lines">
              {formatCount(footerTotals.commentLines)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-blank_lines">
              {formatCount(footerTotals.blankLines)}
            </td>
            <td className="text-end" data-testid="discovery-directory-explorer-footer-total_lines">
              {formatCount(footerTotals.totalLines)}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
