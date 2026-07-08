import type { ReactNode } from 'react';

/** Flat discovery inventory file row (app-agnostic). */
export type DiscoveryInventoryFile = {
  id: string;
  path: string;
  display_path?: string | null;
  language?: string | null;
  extension?: string | null;
  file_kind?: string | null;
  source_type?: string | null;
  classification?: string | null;
  detected_classification?: string | null;
  classification_signal?: string | null;
  classification_explanation?: string | null;
  override_pattern?: string | null;
  production_bucket?: string | null;
  size_bytes?: number | null;
  line_count?: number | null;
  code_line_count?: number | null;
  comment_line_count?: number | null;
  blank_line_count?: number | null;
  rule_count?: number | null;
  needs_review?: boolean | null;
};

export type FileTypeMappingRow = {
  id?: string;
  pattern: string;
  match_type: string;
  language: string;
  language_key?: string;
  display_type: string;
  file_kind: string;
  default_bucket_hint: string;
  comment_style?: string;
  source?: string;
  enabled?: boolean;
  is_generated_hint?: boolean;
  description?: string;
};

export type {
  DirectorySortColumnId,
  DirectorySortDirection,
  DirectoryTreeNode,
  FlatDirectoryRow,
} from '../utils/directoryTree';

export type DirectoryExplorerActions = {
  onCopyDisplayPath: (displayPath: string) => void;
  onCopyRawPath: (rawPath: string) => void;
  onOverrideClassificationFile: (rawPath: string, displayPath: string, classification: string) => void;
  onOverrideClassificationFolder: (folderRawPath: string, displayPath: string, classification: string) => void;
  onExcludeFile: (rawPath: string) => void;
  onExcludeFolder: (folderRawPath: string) => void;
  onExcludeContainingFolder: (fileRawPath: string, displayPath: string) => void;
  lineContextHref: (rawPath: string) => string;
  pathsDiffer: (displayPath: string, rawPath: string) => boolean;
};

export type DirectoryExplorerRenderers = {
  renderFileTypeIcon: (row: import('../utils/directoryTree').FlatDirectoryRow) => ReactNode;
  renderClassification: (row: import('../utils/directoryTree').FlatDirectoryRow) => ReactNode;
  renderRowActions: (
    items: Array<{ id: string; label: string; icon?: string; onClick?: () => void; href?: string }>,
    testId: string,
  ) => ReactNode;
  renderServerPathSearch?: (props: {
    projectId: string;
    scanRunId: string;
    query: string;
    sourceRootPrefix?: string | null;
    actions: DirectoryExplorerActions;
  }) => ReactNode;
};

export type FileTypesTableProps = {
  rows: FileTypeMappingRow[];
  emptyLabel?: string;
  testId?: string;
  quickFilter?: string;
  onQuickFilterChange?: (value: string) => void;
  renderLanguageCell?: (row: FileTypeMappingRow) => ReactNode;
  renderInfoCell?: (row: FileTypeMappingRow) => ReactNode;
};
