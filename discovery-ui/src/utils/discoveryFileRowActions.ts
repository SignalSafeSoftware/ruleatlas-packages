import type { RowActionItem } from '../types/actions';
import type { DirectoryExplorerActions } from '../types/discovery';
import { containingFolderRawPath, isProjectRootExcludeTarget } from './excludeScope';

export type DiscoveryInventoryFileRow = {
  rawPath: string;
  displayPath: string;
  classification: string;
};

export function buildDiscoveryFileRowActions(
  file: DiscoveryInventoryFileRow,
  sourceRootPrefix: string | null | undefined,
  actions: DirectoryExplorerActions,
): RowActionItem[] {
  const pathsDiffer = actions.pathsDiffer(file.displayPath, file.rawPath);
  const items: RowActionItem[] = [
    {
      id: 'override-classification-file',
      label: 'Override classification for this file',
      icon: 'bi-sliders',
      onClick: () =>
        actions.onOverrideClassificationFile(file.rawPath, file.displayPath, file.classification),
    },
  ];

  items.push(
    ...(pathsDiffer
      ? [
          {
            id: 'copy-display-path',
            label: 'Copy display path',
            icon: 'bi-clipboard',
            onClick: () => actions.onCopyDisplayPath(file.displayPath),
          },
          {
            id: 'copy-raw-path',
            label: 'Copy raw path',
            icon: 'bi-clipboard2',
            onClick: () => actions.onCopyRawPath(file.rawPath),
          },
        ]
      : [
          {
            id: 'copy-path',
            label: 'Copy path',
            icon: 'bi-clipboard',
            onClick: () => actions.onCopyRawPath(file.rawPath),
          },
        ]),
  );

  items.push(
    {
      id: 'line-context',
      label: 'Open Line Context',
      icon: 'bi-file-earmark-code',
      href: actions.lineContextHref(file.rawPath),
    },
    {
      id: 'exclude-file',
      label: 'Exclude file',
      icon: 'bi-file-earmark-x',
      onClick: () => actions.onExcludeFile(file.rawPath),
    },
  );

  const containingFolder = containingFolderRawPath(file.rawPath);
  if (containingFolder !== null) {
    const isProjectRoot = isProjectRootExcludeTarget(
      containingFolder,
      file.displayPath,
      sourceRootPrefix,
    );
    items.push({
      id: 'exclude-containing-folder',
      label: isProjectRoot ? 'Exclude project root' : 'Exclude containing folder',
      icon: 'bi-folder-x',
      onClick: () => actions.onExcludeContainingFolder(file.rawPath, file.displayPath),
    });
  }

  return items;
}
