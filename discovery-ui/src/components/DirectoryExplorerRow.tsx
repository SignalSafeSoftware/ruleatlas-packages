import type { DirectoryExplorerActions, DirectoryExplorerRenderers } from '../types/discovery';
import type { RowActionItem } from '../types/actions';
import { formatInteger } from '../utils/numberFormat';
import { formatBytes } from '../utils/formatBytes';
import {
  directoryNodeKindLabel,
  folderRawPath,
  type FlatDirectoryRow,
} from '../utils/directoryTree';
import { buildDiscoveryFileRowActions } from '../utils/discoveryFileRowActions';
import { DiscoveryRowToggle, DiscoveryRowToggleSpacer } from './DiscoveryRowToggle';

function kindLabel(row: FlatDirectoryRow): string {
  return directoryNodeKindLabel(row);
}

function formatCount(value: number): string {
  return formatInteger(value);
}

function directoryRowActions(
  row: FlatDirectoryRow,
  sourceRootPrefix: string | null | undefined,
  actions: DirectoryExplorerActions,
): RowActionItem[] {
  const rawFolderPath = folderRawPath(row.displayPath, sourceRootPrefix);

  if (row.kind === 'folder') {
    return [
      {
        id: 'override-classification-folder',
        label: 'Override classification for this folder',
        icon: 'bi-sliders',
        onClick: () =>
          actions.onOverrideClassificationFolder(rawFolderPath, row.displayPath, row.classification),
      },
      {
        id: 'exclude-folder',
        label: 'Exclude folder',
        icon: 'bi-folder-x',
        onClick: () => actions.onExcludeFolder(rawFolderPath),
      },
      {
        id: 'copy-folder-path',
        label: 'Copy folder path',
        icon: 'bi-clipboard',
        onClick: () => actions.onCopyRawPath(rawFolderPath),
      },
    ];
  }

  return buildDiscoveryFileRowActions(
    { rawPath: row.rawPath, displayPath: row.displayPath, classification: row.classification },
    sourceRootPrefix,
    actions,
  );
}

export function DirectoryExplorerRow({
  row,
  sourceRootPrefix,
  actions,
  renderers,
  onToggle,
}: Readonly<{
  row: FlatDirectoryRow;
  sourceRootPrefix?: string | null;
  actions: DirectoryExplorerActions;
  renderers: DirectoryExplorerRenderers;
  onToggle: () => void;
}>): React.ReactElement {
  const indent = row.depth * 1.25;
  const rowActionItems = directoryRowActions(row, sourceRootPrefix, actions);
  const actionTestId = `discovery-directory-actions-${row.kind}-${row.name}`;

  return (
    <tr data-testid={`discovery-directory-row-${row.kind}-${row.name}`}>
      <td>
        <div className="d-flex align-items-center gap-2" style={{ paddingLeft: `${indent}rem` }}>
          {row.hasChildren ? (
            <DiscoveryRowToggle
              expanded={row.expanded}
              onToggle={onToggle}
              label={row.name}
              testId={`discovery-directory-toggle-${row.displayPath}`}
            />
          ) : (
            <DiscoveryRowToggleSpacer />
          )}
          {renderers.renderFileTypeIcon(row)}
          <span title={actions.pathsDiffer(row.displayPath, row.rawPath) ? `Display: ${row.displayPath}\nRaw: ${row.rawPath}` : row.displayPath}>
            {row.name}
          </span>
        </div>
      </td>
      <td>{kindLabel(row)}</td>
      <td>{renderers.renderClassification(row)}</td>
      <td className="text-end">{row.kind === 'file' ? '—' : formatCount(row.foldersCount)}</td>
      <td className="text-end">{formatCount(row.filesCount)}</td>
      <td className="text-end">{formatBytes(row.sizeBytes)}</td>
      <td className="text-end">{formatCount(row.codeLines)}</td>
      <td className="text-end">{formatCount(row.commentLines)}</td>
      <td className="text-end">{formatCount(row.blankLines)}</td>
      <td className="text-end">{formatCount(row.totalLines)}</td>
      <td className="text-end">
        {renderers.renderRowActions(rowActionItems, actionTestId)}
      </td>
    </tr>
  );
}
