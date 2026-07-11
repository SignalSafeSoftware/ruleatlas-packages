import { useMemo, useState } from 'react';
import type { DiscoveryInventoryFile, DirectoryExplorerActions, DirectoryExplorerRenderers } from '../types/discovery';
import {
  allExpandableFolderIds,
  buildDirectoryTree,
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
  directoryExplorerEmptyCopy,
  fireAndForget,
} from '../utils/directoryExplorerHelpers';
import {
  DirectoryExplorerTable,
  DirectoryExplorerToolbar,
  type DirectoryColumn,
} from './DirectoryExplorerTable';

type LazyTreeProp = {
  status: {
    recommend_lazy_tree?: boolean;
    needs_materialize?: boolean;
    tree_materialized?: boolean;
    inventory_capped?: boolean;
    total_inventory_count?: number;
    tree_state?: string;
  } | null;
  rootNodes: import('../utils/directoryTree').DirectoryTreeNode[];
  childrenById: Map<string, import('../utils/directoryTree').DirectoryTreeNode[]>;
  loading: boolean;
  materializing?: boolean;
  error: string | null;
  materializeError?: string | null;
  needsMaterialize?: boolean;
  materialize?: () => Promise<void>;
  loadChildren: (node: import('../utils/directoryTree').DirectoryTreeNode) => Promise<void>;
};

const EMPTY_LAZY_TREE: LazyTreeProp = {
  status: null,
  rootNodes: [],
  childrenById: new Map(),
  loading: false,
  materializing: false,
  error: null,
  materializeError: null,
  needsMaterialize: false,
  loadChildren: async () => {},
};

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
  lazyTree?: LazyTreeProp;
  projectId?: string;
  scanRunId?: string;
}>): React.ReactElement {
  const lazyTree = lazyTreeProp ?? EMPTY_LAZY_TREE;
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [filterText, setFilterText] = useState('');
  const [sortColumnId, setSortColumnId] = useState<DirectorySortColumnId>(DEFAULT_DIRECTORY_SORT.columnId);
  const [sortDirection, setSortDirection] = useState<DirectorySortDirection>(DEFAULT_DIRECTORY_SORT.direction);

  const needsMaterialize = Boolean(
    lazyTree.needsMaterialize ||
      lazyTree.status?.needs_materialize ||
      (inventoryCapped && lazyTree.status && !lazyTree.status.tree_materialized),
  );
  const useLazyTree = Boolean(
    inventoryCapped && lazyTree.status?.recommend_lazy_tree && !lazyTree.loading && !needsMaterialize,
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
  const emptyInventory = useLazyTree
    ? lazyTree.rootNodes.length === 0 && !lazyTree.loading && !lazyTree.materializing
    : files.length === 0 && !needsMaterialize;
  const filterEmpty = filterActive && visibleRows.length === 0;
  const showServerKeywordSearch = Boolean(projectId && scanRunId && filterText.trim());
  const explorerDescription = directoryExplorerDescription({
    inventoryCapped,
    useLazyTree,
    showServerKeywordSearch,
    needsMaterialize,
  });
  const emptyCopy = directoryExplorerEmptyCopy({
    needsMaterialize,
    inventoryCapped,
    totalInventoryCount: lazyTree.status?.total_inventory_count,
  });

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

  return (
    <div data-testid="discovery-directory-explorer">
      <h3 className="h6 mb-1">Directory explorer</h3>
      <p className="small text-body-secondary mb-2">{explorerDescription}</p>

      {needsMaterialize ? (
        <div className="alert alert-info py-2" data-testid="discovery-directory-needs-materialize">
          <p className="small mb-2">
            Inventory exists for this scan ({lazyTree.status?.total_inventory_count ?? 'many'} files),
            but the full directory tree is not materialized yet. The table below may show only a capped
            sample until you build the tree.
          </p>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            data-testid="discovery-directory-materialize-cta"
            disabled={Boolean(lazyTree.materializing) || !lazyTree.materialize}
            onClick={() => {
              if (lazyTree.materialize) {
                fireAndForget(lazyTree.materialize());
              }
            }}
          >
            {lazyTree.materializing ? 'Building directory tree…' : 'Build directory tree'}
          </button>
          {lazyTree.materializeError ? (
            <p className="small text-danger mb-0 mt-2" data-testid="discovery-directory-materialize-error">
              {lazyTree.materializeError}
              {' '}
              Editor/scan permission may be required to materialize the tree.
            </p>
          ) : null}
        </div>
      ) : null}

      {lazyTree.error ? (
        <p className="small text-danger mb-2" data-testid="discovery-directory-lazy-tree-error">
          {lazyTree.error}
        </p>
      ) : null}
      {(useLazyTree && lazyTree.loading) || lazyTree.materializing ? (
        <p className="small text-body-secondary mb-2" data-testid="discovery-directory-lazy-tree-loading">
          {lazyTree.materializing ? 'Building directory tree…' : 'Loading directory tree…'}
        </p>
      ) : null}

      <DirectoryExplorerToolbar
        filterText={filterText}
        onFilterChange={setFilterText}
        onExpandAll={() => setExpanded(new Set(allExpandableFolderIds(sortedTree)))}
        onCollapseAll={() => setExpanded(new Set())}
        onExpandTopLevel={() => setExpanded(new Set(topLevelFolderIds(sortedTree)))}
      />

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
          {emptyCopy}
        </p>
      ) : (
        <DirectoryExplorerTable
          files={files}
          filterText={filterText}
          filterActive={filterActive}
          visibleRows={visibleRows}
          filterEmpty={filterEmpty}
          sortColumnId={sortColumnId}
          sortDirection={sortDirection}
          onToggleSort={toggleSort}
          sortIndicator={sortIndicator}
          sourceRootPrefix={sourceRootPrefix}
          actions={actions}
          renderers={renderers}
          onToggleExpanded={toggleExpanded}
        />
      )}
    </div>
  );
}
