import type { DirectorySortDirection } from '../utils/directoryTree';

export function directorySortAriaValue(
  sortable: boolean,
  isActive: boolean,
  direction: DirectorySortDirection,
): 'ascending' | 'descending' | undefined {
  if (!sortable || !isActive) return undefined;
  return direction === 'asc' ? 'ascending' : 'descending';
}

export function directoryExplorerDescription(options: {
  inventoryCapped?: boolean;
  useLazyTree: boolean;
  showServerKeywordSearch: boolean;
  needsMaterialize?: boolean;
}): string {
  const parts = [
    'Expandable directory tree grouped by display path. Folder rows aggregate child folders, files, and sizes.',
    'All inventoried files are shown; exclude globs in scan scope omit paths from inventory entirely.',
  ];
  if (options.needsMaterialize) {
    parts.push(
      'Inventory exists, but the full directory tree is not built yet for this large scan. Use Build directory tree to materialize server nodes, then expand folders to browse.',
    );
  } else if (options.inventoryCapped) {
    parts.push('Tree reflects the capped inventory sample shown in the workspace.');
  }
  if (options.useLazyTree) {
    parts.push(
      'Large inventory — directory tree loads lazily from materialized server nodes. Expand folders to load children.',
    );
  }
  if (options.showServerKeywordSearch) {
    parts.push(
      'Keyword search below queries the full saved inventory via server paging (path, classification, language, source type).',
    );
  }
  return parts.join(' ');
}

export function directoryExplorerEmptyCopy(options: {
  needsMaterialize?: boolean;
  inventoryCapped?: boolean;
  totalInventoryCount?: number | null;
}): string {
  if (options.needsMaterialize) {
    return 'Inventory files exist for this scan, but the navigable directory tree has not been built yet.';
  }
  if ((options.totalInventoryCount ?? 0) > 0 || options.inventoryCapped) {
    return 'No folders are visible in this tree view yet. Try clearing filters or building the directory tree.';
  }
  return 'No discovery inventory found. Run discovery to inventory files.';
}

export function fireAndForget(promise: Promise<unknown>): void {
  promise.catch(() => undefined);
}
