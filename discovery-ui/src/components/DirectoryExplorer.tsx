import { useMemo, useState } from 'react';
import type { DiscoveryInventoryFile, DirectoryExplorerActions, DirectoryExplorerRenderers } from '../types/discovery';
import { formatInteger } from '../utils/numberFormat';
import { formatBytes } from '../utils/formatBytes';
import {
  allExpandableFolderIds,
  buildDirectoryTree,
  computeDirectoryExplorerTotals,
  sumDirectoryExplorerSubfoldersFooter,
  DEFAULT_DIRECTORY_SORT,
  flattenVisibleTree,
  flattenLazyVisibleTree,
  sortDirectoryTree,
  topLevelFolderIds,
  type DirectorySortColumnId,
  type DirectorySortDirection,
  type FlatDirectoryRow,
} from '../utils/directoryTree';
import {
  directoryExplorerDescription,
  directorySortAriaValue,
  fireAndForget,
} from '../utils/directoryExplorerHelpers';
import { DirectoryExplorerRow } from './DirectoryExplorerRow';

function formatCount(value: number): string {
  return formatInteger(value);
}

type DirectoryColumn = {
  id: DirectorySortColumnId | 'actions';
  label: string;
  align?: 'start' | 'end';
  sortable?: boolean;
  headerTitle?: string;
};

const DIRECTORY_COLUMNS: DirectoryColumn[] = [
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


export function DirectoryExplorer({
  files,
  inventoryCapped,
  sourceRootPrefix,
  actions,
  renderers,
  lazyTree: lazyTreeProp,
  projectId,
  scanRunId,
}: Readonly<{
  files: DiscoveryInventoryFile[];
  inventoryCapped?: boolean;
  sourceRootPrefix?: string | null;
  actions: DirectoryExplorerActions;
  renderers: DirectoryExplorerRenderers;
  lazyTree?: {
    status: { recommend_lazy_tree?: boolean } | null;
    rootNodes: import('../utils/directoryTree').DirectoryTreeNode[];
    childrenById: Map<string, import('../utils/directoryTree').DirectoryTreeNode[]>;
    loading: boolean;
    error: string | null;
    loadChildren: (node: import('../utils/directoryTree').DirectoryTreeNode) => Promise<void>;
  };
  projectId?: string;
  scanRunId?: string;
}>): React.ReactElement {
  const lazyTree = lazyTreeProp ?? {
    status: null,
    rootNodes: [],
    childrenById: new Map(),
    loading: false,
    error: null,
    loadChildren: async () => {},
  };
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [filterText, setFilterText] = useState('');
  const [sortColumnId, setSortColumnId] = useState<DirectorySortColumnId>(DEFAULT_DIRECTORY_SORT.columnId);
  const [sortDirection, setSortDirection] = useState<DirectorySortDirection>(DEFAULT_DIRECTORY_SORT.direction);

  const useLazyTree = Boolean(
    inventoryCapped && lazyTree.status?.recommend_lazy_tree && !lazyTree.loading,
  );

  const tree = useMemo(() => (useLazyTree ? [] : buildDirectoryTree(files)), [files, useLazyTree]);
  const sortedTree = useMemo(
    () => sortDirectoryTree(tree, sortColumnId, sortDirection),
    [tree, sortColumnId, sortDirection],
  );
  const visibleRows = useMemo(() => {
    if (useLazyTree) {
      return flattenLazyVisibleTree(
        lazyTree.rootNodes,
        expanded,
        lazyTree.childrenById,
        filterText,
      );
    }
    return flattenVisibleTree(sortedTree, expanded, filterText);
  }, [
    expanded,
    filterText,
    lazyTree.childrenById,
    lazyTree.rootNodes,
    sortedTree,
    useLazyTree,
  ]);
  const filterActive = filterText.trim().length > 0;
  const footerTotals = useMemo(
    () => computeDirectoryExplorerTotals(files, filterText),
    [files, filterText],
  );
  const subfoldersFooterTotal = useMemo(
    () => sumDirectoryExplorerSubfoldersFooter(visibleRows, { filterActive }),
    [filterActive, visibleRows],
  );

  function toggleSort(column: DirectoryColumn): void {
    if (column.sortable === false || column.id === 'actions') return;
    const columnId = column.id as DirectorySortColumnId;
    if (sortColumnId === columnId) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortColumnId(columnId);
    setSortDirection(column.align === 'end' ? 'desc' : 'asc');
  }

  function sortIndicator(columnId: string): string {
    if (sortColumnId !== columnId) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  }

  function toggleExpanded(id: string, row?: FlatDirectoryRow): void {
    if (useLazyTree && row?.kind === 'folder') {
      fireAndForget(lazyTree.loadChildren(row));
    }
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function expandAll(): void {
    setExpanded(new Set(allExpandableFolderIds(sortedTree)));
  }

  function collapseAll(): void {
    setExpanded(new Set());
  }

  function expandTopLevel(): void {
    setExpanded(new Set(topLevelFolderIds(sortedTree)));
  }

  const emptyInventory = useLazyTree ? lazyTree.rootNodes.length === 0 && !lazyTree.loading : files.length === 0;
  const filterEmpty = filterActive && visibleRows.length === 0;
  const showServerKeywordSearch = Boolean(projectId && scanRunId && filterText.trim());
  const explorerDescription = directoryExplorerDescription({
    inventoryCapped,
    useLazyTree,
    showServerKeywordSearch,
  });

  return (
    <div data-testid="discovery-directory-explorer">
      <h3 className="h6 mb-1">Directory explorer</h3>
        <p className="small text-body-secondary mb-2">{explorerDescription}</p>

        {lazyTree.error ? (
          <p className="small text-danger mb-2" data-testid="discovery-directory-lazy-tree-error">
            {lazyTree.error}
          </p>
        ) : null}
        {useLazyTree && lazyTree.loading ? (
          <p className="small text-body-secondary mb-2" data-testid="discovery-directory-lazy-tree-loading">
            Loading directory tree…
          </p>
        ) : null}

        <div className="d-flex flex-wrap gap-2 mb-2 align-items-center">
          <input
            className="form-control form-control-sm"
            style={{ maxWidth: '24rem' }}
            placeholder="Inventory keyword search (path, classification, language…)"
            value={filterText}
            onChange={(event) => setFilterText(event.target.value)}
            data-testid="discovery-directory-explorer-filter"
          />
          <button type="button" className="btn btn-secondary btn-sm" onClick={expandAll}>
            Expand all
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={collapseAll}>
            Collapse all
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={expandTopLevel}>
            Expand top level
          </button>
        </div>

        {showServerKeywordSearch && renderers.renderServerPathSearch
          ? renderers.renderServerPathSearch({
              projectId: projectId!,
              scanRunId: scanRunId!,
              query: filterText,
              sourceRootPrefix,
              actions,
            })
          : null}

        {emptyInventory ? (
          <p className="small text-body-secondary mb-0" data-testid="discovery-directory-explorer-empty">
            No discovery inventory found. Run discovery to inventory files.
          </p>
        ) : (
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
                            onClick={() => toggleSort(column)}
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
                      onToggle={() => toggleExpanded(row.id, row)}
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
        )}
    </div>
  );
}
