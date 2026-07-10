import type { DiscoveryInventoryFile } from '../types/discovery';
import { humanizeToken } from './humanizeToken';

export type DirectorySortColumnId =
  | 'name'
  | 'kind'
  | 'classification'
  | 'folders'
  | 'files'
  | 'size_bytes'
  | 'code_lines'
  | 'comment_lines'
  | 'blank_lines'
  | 'total_lines';

export type DirectorySortDirection = 'asc' | 'desc';

export const DEFAULT_DIRECTORY_SORT: {
  columnId: DirectorySortColumnId;
  direction: DirectorySortDirection;
} = {
  columnId: 'name',
  direction: 'asc',
};

export type DirectoryTreeNode = {
  id: string;
  kind: 'folder' | 'file';
  name: string;
  displayPath: string;
  rawPath: string;
  depth: number;
  language: string;
  extension: string;
  fileKind: string;
  classification: string;
  detectedClassification?: string;
  classificationSignal?: string | null;
  classificationExplanation?: string | null;
  overridePattern?: string | null;
  bucket: string;
  foldersCount: number;
  filesCount: number;
  sizeBytes: number;
  codeLines: number;
  commentLines: number;
  blankLines: number;
  totalLines: number;
  ruleCount: number;
  needsReviewCount: number;
  fileId?: string;
  children: DirectoryTreeNode[];
};

export type FlatDirectoryRow = DirectoryTreeNode & {
  hasChildren: boolean;
  expanded: boolean;
};

type MutableFolder = {
  displayPath: string;
  name: string;
  depth: number;
  childFolders: Map<string, MutableFolder>;
  files: NormalizedFile[];
};

type NormalizedFile = {
  id: string;
  displayPath: string;
  rawPath: string;
  name: string;
  depth: number;
  language: string;
  extension: string;
  fileKind: string;
  classification: string;
  detectedClassification?: string;
  classificationSignal?: string | null;
  classificationExplanation?: string | null;
  overridePattern?: string | null;
  bucket: string;
  sizeBytes: number;
  codeLines: number;
  commentLines: number;
  blankLines: number;
  totalLines: number;
  ruleCount: number;
  needsReview: boolean;
};

const NEEDS_REVIEW_CLASSIFICATION = 'unknown_needs_review';

export function extensionFromPath(path: string): string {
  const base = path.split('/').pop() ?? path;
  const dot = base.lastIndexOf('.');
  if (dot <= 0) return '(none)';
  return base.slice(dot);
}

function sizeValue(value: number | null | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : 0;
}

function lineValue(value: number | null | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

export function normalizeDiscoveryFile(file: DiscoveryInventoryFile): NormalizedFile {
  const displayPath = file.display_path || file.path;
  const rawPath = file.path;
  const segments = displayPath.split('/').filter(Boolean);
  const name = segments.at(-1) ?? displayPath;
  return {
    id: file.id,
    displayPath,
    rawPath,
    name,
    depth: Math.max(0, segments.length - 1),
    language: file.language ?? 'unknown',
    extension: extensionFromPath(displayPath),
    fileKind: file.file_kind ?? file.source_type ?? 'unknown',
    classification: file.classification ?? 'unknown',
    detectedClassification: file.detected_classification ?? file.classification ?? undefined,
    classificationSignal: file.classification_signal ?? null,
    classificationExplanation: file.classification_explanation ?? null,
    overridePattern: file.override_pattern ?? null,
    bucket: file.production_bucket ?? 'unknown',
    sizeBytes: sizeValue(file.size_bytes),
    codeLines: lineValue(file.code_line_count),
    commentLines: lineValue(file.comment_line_count),
    blankLines: lineValue(file.blank_line_count),
    totalLines: lineValue(file.line_count),
    ruleCount: lineValue(file.rule_count),
    needsReview: file.classification === NEEDS_REVIEW_CLASSIFICATION,
  };
}

function dominantBucket(counts: Map<string, number>): string {
  if (counts.size === 0) return '—';
  if (counts.size === 1) return [...counts.keys()][0];
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  if (sorted.length > 1 && sorted[0][1] === sorted[1][1]) return 'Mixed';
  return sorted[0][0];
}

function dominantClassification(classifications: Set<string>): string {
  if (classifications.size === 0) return '—';
  if (classifications.size === 1) return [...classifications][0];
  return 'Mixed';
}

function aggregateMetrics(nodes: DirectoryTreeNode[]): Omit<
  DirectoryTreeNode,
  'id' | 'kind' | 'name' | 'displayPath' | 'rawPath' | 'depth' | 'language' | 'extension' | 'fileKind' | 'children' | 'fileId'
> {
  const bucketCounts = new Map<string, number>();
  const classifications = new Set<string>();
  let codeLines = 0;
  let commentLines = 0;
  let blankLines = 0;
  let totalLines = 0;
  let ruleCount = 0;
  let needsReviewCount = 0;
  let filesCount = 0;
  let sizeBytes = 0;

  for (const node of nodes) {
    if (node.kind === 'file') {
      classifications.add(node.classification);
      bucketCounts.set(node.bucket, (bucketCounts.get(node.bucket) ?? 0) + 1);
      filesCount += 1;
    } else {
      filesCount += node.filesCount;
    }
    sizeBytes += node.sizeBytes;
    codeLines += node.codeLines;
    commentLines += node.commentLines;
    blankLines += node.blankLines;
    totalLines += node.totalLines;
    ruleCount += node.ruleCount;
    needsReviewCount += node.needsReviewCount;
  }

  const foldersCount = nodes.filter((node) => node.kind === 'folder').length;

  return {
    classification: dominantClassification(classifications),
    bucket: dominantBucket(bucketCounts),
    foldersCount,
    filesCount,
    sizeBytes,
    codeLines,
    commentLines,
    blankLines,
    totalLines,
    ruleCount,
    needsReviewCount,
  };
}

function fileToNode(file: NormalizedFile): DirectoryTreeNode {
  return {
    id: `file:${file.displayPath}`,
    kind: 'file',
    name: file.name,
    displayPath: file.displayPath,
    rawPath: file.rawPath,
    depth: file.depth,
    language: file.language,
    extension: file.extension,
    fileKind: file.fileKind,
    classification: file.classification,
    detectedClassification: file.detectedClassification,
    classificationSignal: file.classificationSignal,
    classificationExplanation: file.classificationExplanation,
    overridePattern: file.overridePattern,
    bucket: file.bucket,
    foldersCount: 0,
    filesCount: 1,
    sizeBytes: file.sizeBytes,
    codeLines: file.codeLines,
    commentLines: file.commentLines,
    blankLines: file.blankLines,
    totalLines: file.totalLines,
    ruleCount: file.ruleCount,
    needsReviewCount: file.needsReview ? 1 : 0,
    fileId: file.id,
    children: [],
  };
}

function compareSortValues(a: number | string, b: number | string, direction: DirectorySortDirection): number {
  const factor = direction === 'asc' ? 1 : -1;
  if (typeof a === 'number' && typeof b === 'number') {
    return (a - b) * factor;
  }
  return String(a).localeCompare(String(b), undefined, { sensitivity: 'base' }) * factor;
}

/** Explorer group: hidden folders → visible folders → hidden files → visible files. */
export function getExplorerSortGroup(node: DirectoryTreeNode): number {
  const isHidden = node.name.startsWith('.');
  const isFolder = node.kind === 'folder';
  if (isHidden && isFolder) return 0;
  if (!isHidden && isFolder) return 1;
  if (isHidden && !isFolder) return 2;
  return 3;
}

/** Case-insensitive natural sort for sibling basenames (icons/indent ignored). */
export function naturalCompare(a: string, b: string): number {
  return a.toLowerCase().localeCompare(b.toLowerCase(), undefined, { numeric: true, sensitivity: 'base' });
}

function classificationSortValue(value: string): string {
  if (value === '—' || value === 'Mixed') return value;
  return value.replaceAll('_', ' ');
}

export function directoryNodeKindLabel(node: DirectoryTreeNode): string {
  if (node.kind !== 'file') return 'Folder';
  const kind = node.fileKind.trim();
  if (!kind || kind === '—') return '—';
  return humanizeToken(kind);
}

export function directoryNodeSortValue(
  node: DirectoryTreeNode,
  columnId: DirectorySortColumnId,
): number | string {
  switch (columnId) {
    case 'name':
      return node.name;
    case 'kind':
      return directoryNodeKindLabel(node);
    case 'classification':
      return classificationSortValue(node.classification);
    case 'folders':
      return node.kind === 'file' ? -1 : node.foldersCount;
    case 'files':
      return node.filesCount;
    case 'size_bytes':
      return node.sizeBytes;
    case 'code_lines':
      return node.codeLines;
    case 'comment_lines':
      return node.commentLines;
    case 'blank_lines':
      return node.blankLines;
    case 'total_lines':
      return node.totalLines;
    default:
      return node.name;
  }
}

export function compareDirectoryNodes(
  a: DirectoryTreeNode,
  b: DirectoryTreeNode,
  columnId: DirectorySortColumnId,
  direction: DirectorySortDirection,
): number {
  const groupDiff = getExplorerSortGroup(a) - getExplorerSortGroup(b);
  if (groupDiff !== 0) return groupDiff;

  if (columnId === 'name') {
    const nameDiff = naturalCompare(a.name, b.name);
    return direction === 'asc' ? nameDiff : -nameDiff;
  }

  const primary = compareSortValues(
    directoryNodeSortValue(a, columnId),
    directoryNodeSortValue(b, columnId),
    direction,
  );
  if (primary !== 0) return primary;
  return naturalCompare(a.name, b.name);
}

export function sortDirectoryTree(
  nodes: DirectoryTreeNode[],
  columnId: DirectorySortColumnId = DEFAULT_DIRECTORY_SORT.columnId,
  direction: DirectorySortDirection = DEFAULT_DIRECTORY_SORT.direction,
): DirectoryTreeNode[] {
  const sorted = [...nodes].sort((left, right) => compareDirectoryNodes(left, right, columnId, direction));
  return sorted.map((node) =>
    node.children.length > 0
      ? { ...node, children: sortDirectoryTree(node.children, columnId, direction) }
      : node,
  );
}

function finalizeFolder(folder: MutableFolder): DirectoryTreeNode {
  const childFolderNodes = [...folder.childFolders.values()].map(finalizeFolder);
  const fileNodes = folder.files.map(fileToNode);
  const children = sortDirectoryTree([...childFolderNodes, ...fileNodes]);
  const metrics = aggregateMetrics(children);

  return {
    id: `folder:${folder.displayPath}`,
    kind: 'folder',
    name: folder.name,
    displayPath: folder.displayPath,
    rawPath: folder.displayPath,
    depth: folder.depth,
    language: '—',
    extension: '—',
    fileKind: '—',
    classification: metrics.classification,
    bucket: metrics.bucket,
    foldersCount: childFolderNodes.length,
    filesCount: metrics.filesCount,
    sizeBytes: metrics.sizeBytes,
    codeLines: metrics.codeLines,
    commentLines: metrics.commentLines,
    blankLines: metrics.blankLines,
    totalLines: metrics.totalLines,
    ruleCount: metrics.ruleCount,
    needsReviewCount: metrics.needsReviewCount,
    children,
  };
}

export function sortSiblingNodes(nodes: DirectoryTreeNode[]): DirectoryTreeNode[] {
  return sortDirectoryTree(nodes);
}

export function buildDirectoryTree(files: DiscoveryInventoryFile[]): DirectoryTreeNode[] {
  const rootFolders = new Map<string, MutableFolder>();
  const rootFiles: NormalizedFile[] = [];

  function ensureFolder(parentMap: Map<string, MutableFolder>, segment: string, pathSoFar: string): MutableFolder {
    if (!parentMap.has(segment)) {
      parentMap.set(segment, {
        displayPath: pathSoFar,
        name: segment,
        depth: pathSoFar.split('/').filter(Boolean).length - 1,
        childFolders: new Map(),
        files: [],
      });
    }
    return parentMap.get(segment)!;
  }

  for (const file of files) {
    const normalized = normalizeDiscoveryFile(file);
    const segments = normalized.displayPath.split('/').filter(Boolean);
    if (segments.length <= 1) {
      rootFiles.push({ ...normalized, name: segments[0] ?? normalized.displayPath });
      continue;
    }

    segments.pop();
    let currentMap = rootFolders;
    let pathSoFar = '';
    let folder: MutableFolder | null = null;

    for (const segment of segments) {
      pathSoFar = pathSoFar ? `${pathSoFar}/${segment}` : segment;
      folder = ensureFolder(currentMap, segment, pathSoFar);
      currentMap = folder.childFolders;
    }

    if (folder) {
      folder.files.push(normalized);
    }
  }

  const roots = [...rootFolders.values()].map(finalizeFolder);
  const rootFileNodes = rootFiles.map(fileToNode);
  return sortDirectoryTree([...roots, ...rootFileNodes]);
}

function nodeSearchValues(node: DirectoryTreeNode): string[] {
  if (node.kind === 'folder') {
    return [node.name, node.displayPath, node.classification, node.bucket];
  }
  return [
    node.name,
    node.displayPath,
    node.rawPath,
    node.extension,
    node.language,
    node.classification,
    node.bucket,
    node.fileKind,
  ];
}

export function nodeMatchesFilter(node: DirectoryTreeNode, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return nodeSearchValues(node).some((value) => value?.toLowerCase().includes(q));
}

export function collectMatchingPaths(nodes: DirectoryTreeNode[], query: string): Set<string> {
  const matches = new Set<string>();
  const q = query.trim().toLowerCase();
  if (!q) return matches;

  function walk(node: DirectoryTreeNode): boolean {
    const selfMatch = nodeMatchesFilter(node, q);
    let childMatch = false;
    for (const child of node.children) {
      if (walk(child)) {
        childMatch = true;
      }
    }
    if (selfMatch || childMatch) {
      matches.add(node.id);
      return true;
    }
    return false;
  }

  for (const node of nodes) {
    walk(node);
  }
  return matches;
}

export function collectAncestorIds(nodes: DirectoryTreeNode[], targetId: string): string[] {
  const path: string[] = [];

  function walk(node: DirectoryTreeNode): boolean {
    path.push(node.id);
    if (node.id === targetId) {
      return true;
    }
    for (const child of node.children) {
      if (walk(child)) {
        return true;
      }
    }
    path.pop();
    return false;
  }

  for (const node of nodes) {
    path.length = 0;
    if (walk(node)) {
      return path.slice(0, -1);
    }
  }
  return [];
}

export function flattenLazyVisibleTree(
  rootNodes: DirectoryTreeNode[],
  expanded: Set<string>,
  childrenById: Map<string, DirectoryTreeNode[]>,
  filterQuery: string,
): FlatDirectoryRow[] {
  const q = filterQuery.trim().toLowerCase();
  const rows: FlatDirectoryRow[] = [];

  function walk(nodes: DirectoryTreeNode[]): void {
    const sorted = sortSiblingNodes(nodes);
    for (const node of sorted) {
      if (q) {
        const selfMatch = nodeMatchesFilter(node, q);
        const children = childrenById.get(node.id) ?? [];
        const childMatch = children.some((child) => nodeMatchesFilter(child, q));
        if (!selfMatch && !(node.kind === 'folder' && (childMatch || expanded.has(node.id)))) {
          continue;
        }
      }
      const children = childrenById.get(node.id) ?? [];
      const hasChildren = node.kind === 'folder' && (children.length > 0 || node.foldersCount > 0 || node.filesCount > 0);
      const expandedNode = q ? true : expanded.has(node.id);
      rows.push({
        ...node,
        hasChildren,
        expanded: expandedNode,
      });
      if (hasChildren && expandedNode) {
        walk(children);
      }
    }
  }

  walk(rootNodes);
  return rows;
}

export function flattenVisibleTree(
  nodes: DirectoryTreeNode[],
  expanded: Set<string>,
  filterQuery: string,
): FlatDirectoryRow[] {
  const q = filterQuery.trim().toLowerCase();
  const textMatchingIds = q ? collectMatchingPaths(nodes, q) : null;
  const rows: FlatDirectoryRow[] = [];

  function walk(nodeList: DirectoryTreeNode[], autoExpand: boolean): void {
    for (const node of nodeList) {
      if (textMatchingIds && !textMatchingIds.has(node.id)) {
        continue;
      }

      const hasChildren = node.children.length > 0;
      const expandedNode = autoExpand || expanded.has(node.id);
      rows.push({
        ...node,
        hasChildren,
        expanded: expandedNode,
      });

      if (hasChildren && expandedNode) {
        walk(node.children, autoExpand);
      }
    }
  }

  walk(nodes, Boolean(q));
  return rows;
}

export function allExpandableFolderIds(nodes: DirectoryTreeNode[]): string[] {
  const ids: string[] = [];
  function walk(nodeList: DirectoryTreeNode[]): void {
    for (const node of nodeList) {
      if (node.kind === 'folder' && node.children.length > 0) {
        ids.push(node.id);
        walk(node.children);
      }
    }
  }
  walk(nodes);
  return ids;
}

export function topLevelFolderIds(nodes: DirectoryTreeNode[]): string[] {
  return nodes.filter((node) => node.kind === 'folder').map((node) => node.id);
}

export function folderRawPath(displayPath: string, sourceRootPrefix: string | null | undefined): string {
  if (!sourceRootPrefix) return displayPath;
  return `${sourceRootPrefix}/${displayPath}`;
}

export type DirectoryExplorerTotals = {
  files: number;
  sizeBytes: number;
  codeLines: number;
  commentLines: number;
  blankLines: number;
  totalLines: number;
  filterActive: boolean;
};

/**
 * Subfolders footer: sum of Subfolders column values for displayed rows.
 * Default view uses top-level folder rows only so expand/collapse does not double-count.
 * Filtered view skips parent folder rows when child folders are also visible.
 */
export function sumDirectoryExplorerSubfoldersFooter(
  visibleRows: FlatDirectoryRow[],
  options: { filterActive: boolean },
): number {
  const visibleIds = new Set(visibleRows.map((row) => row.id));
  let sum = 0;
  for (const row of visibleRows) {
    if (row.kind !== 'folder') continue;
    if (!options.filterActive && row.depth !== 0) continue;
    if (options.filterActive) {
      const hasVisibleChildFolder = row.children.some(
        (child) => child.kind === 'folder' && visibleIds.has(child.id),
      );
      if (hasVisibleChildFolder) continue;
    }
    sum += row.foldersCount;
  }
  return sum;
}

/** Sum inventory once from tree leaf files; respects directory filter without expand/collapse double-counting. */
export function computeDirectoryExplorerTotals(
  files: DiscoveryInventoryFile[],
  filterQuery: string,
): DirectoryExplorerTotals {
  const tree = buildDirectoryTree(files);
  const q = filterQuery.trim().toLowerCase();
  const matchingIds = q ? collectMatchingPaths(tree, q) : null;

  let filesCount = 0;
  let sizeBytes = 0;
  let codeLines = 0;
  let commentLines = 0;
  let blankLines = 0;
  let totalLines = 0;

  function walk(nodeList: DirectoryTreeNode[]): void {
    for (const node of nodeList) {
      if (matchingIds && !matchingIds.has(node.id)) continue;
      if (node.kind === 'file') {
        filesCount += 1;
        sizeBytes += node.sizeBytes;
        codeLines += node.codeLines;
        commentLines += node.commentLines;
        blankLines += node.blankLines;
        totalLines += node.totalLines;
      }
      walk(node.children);
    }
  }

  walk(tree);

  return {
    files: filesCount,
    sizeBytes,
    codeLines,
    commentLines,
    blankLines,
    totalLines,
    filterActive: Boolean(q),
  };
}
