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
  fireAndForget,
} from '../utils/directoryExplorerHelpers';
import {
  DirectoryExplorerTable,
  DirectoryExplorerToolbar,
  type DirectoryColumn,
} from './DirectoryExplorerTable';

type LazyTreeProp = {
  status: { recommend_lazy_tree?: boolean } | null;
  rootNodes: import('../utils/directoryTree').DirectoryTreeNode[];
  childrenById: Map<string, import('../utils/directoryTree').DirectoryTreeNode[]>;
  loading: boolean;
  error: string | null;
  loadChildren: (node: import('../utils/directoryTree').DirectoryTreeNode) => Promise<void>;
};

const EMPTY_LAZY_TREE: LazyTreeProp = {
  status: null,
  rootNodes: [],
  childrenById: new Map(),
  loading: false,
  error: null,
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
  const emptyInventory = useLazyTree
    ? lazyTree.rootNodes.length === 0 && !lazyTree.loading
    : files.length === 0;
  const filterEmpty = filterActive && visibleRows.length === 0;
  const showServerKeywordSearch = Boolean(projectId && scanRunId && filterText.trim());
  const explorerDescription = directoryExplorerDescription({
    inventoryCapped,
    useLazyTree,
    showServerKeywordSearch,
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
          No discovery inventory found. Run discovery to inventory files.
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
