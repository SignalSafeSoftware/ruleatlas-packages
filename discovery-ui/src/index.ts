export { DirectoryExplorer } from './components/DirectoryExplorer';
export {
  DiscoveryMetricsTable,
  formatPercent,
  bucketLabel,
  BUCKET_LABELS,
  type MetricsTableColumn,
  type MetricsTableExpandable,
  type MetricsTableFooterContext,
  type MetricsTableFooterSpec,
  type MetricsTableScopeOption,
  type SortDirection,
  type TieBreaker,
} from './components/DiscoveryMetricsTable';
export { DiscoveryRowToggle, DiscoveryRowToggleSpacer } from './components/DiscoveryRowToggle';
export { FileTypeBadge, FileTypesTable } from './components/FileTypesTable';
export { LineCountByFileTypeTable, type LineCountByFileTypeTableProps } from './components/LineCountByFileTypeTable';
export type { RowActionItem } from './types/actions';
export type {
  DiscoveryInventoryFile,
  DirectoryExplorerActions,
  DirectoryExplorerRenderers,
  FileTypeMappingRow,
  FileTypesTableProps,
} from './types/discovery';
export {
  allExpandableFolderIds,
  buildDirectoryTree,
  computeDirectoryExplorerTotals,
  DEFAULT_DIRECTORY_SORT,
  directoryNodeKindLabel,
  extensionFromPath,
  flattenLazyVisibleTree,
  flattenVisibleTree,
  folderRawPath,
  getExplorerSortGroup,
  naturalCompare,
  normalizeDiscoveryFile,
  sortDirectoryTree,
  sortSiblingNodes,
  sumDirectoryExplorerSubfoldersFooter,
  topLevelFolderIds,
  type DirectorySortColumnId,
  type DirectorySortDirection,
  type DirectoryTreeNode,
  type FlatDirectoryRow,
} from './utils/directoryTree';
export { buildDiscoveryFileRowActions, type DiscoveryInventoryFileRow } from './utils/discoveryFileRowActions';
export {
  buildExcludeConfirmMessage,
  containingFolderDisplayPath,
  containingFolderRawPath,
  fileExcludeGlob,
  folderExcludeGlob,
  isProjectRootExcludeTarget,
  type ExcludeConfirmKind,
} from './utils/excludeScope';
export { formatBytes } from './utils/formatBytes';
export { humanizeToken, humanizeTokenLower } from './utils/humanizeToken';
export { formatInteger } from './utils/numberFormat';
