/** Pure path/glob helpers for discovery exclude scope (no browser UI). */

export function containingFolderRawPath(fileRawPath: string): string | null {
  const index = fileRawPath.lastIndexOf('/');
  if (index < 0) return null;
  return fileRawPath.slice(0, index);
}

export function containingFolderDisplayPath(fileDisplayPath: string): string | null {
  const index = fileDisplayPath.lastIndexOf('/');
  if (index < 0) return null;
  return fileDisplayPath.slice(0, index);
}

export function folderExcludeGlob(folderRawPath: string): string {
  return `${folderRawPath}/**`;
}

export function fileExcludeGlob(rawPath: string): string {
  return `**/${rawPath}`;
}

/** True when excluding the containing folder would drop the whole project/archive root. */
export function isProjectRootExcludeTarget(
  folderRawPath: string,
  fileDisplayPath: string,
  sourceRootPrefix?: string | null,
): boolean {
  if (!fileDisplayPath.includes('/')) {
    return true;
  }
  if (sourceRootPrefix && folderRawPath === sourceRootPrefix) {
    return true;
  }
  return false;
}

export type ExcludeConfirmKind = 'file' | 'folder' | 'project-root';

  /** Message body for exclude confirmation dialogs (host app shows the dialog). */
export function buildExcludeConfirmMessage(
  glob: string,
  options: { kind: ExcludeConfirmKind; friendlyPath?: string },
): string {
  const prefix = options.friendlyPath ? `${options.friendlyPath}\n\n` : '';
  if (options.kind === 'project-root') {
    return (
      `${prefix}Exclude entire project root from scan scope?\n\nExclude glob:\n${glob}\n\n` +
      'This affects all files under this root. Source files are not deleted.'
    );
  }
  const target = options.kind === 'file' ? 'file' : 'folder';
  return (
    `${prefix}Add exclude glob for this ${target}?\n\n${glob}\n\n` +
    'Updates scan scope only. Source files are not deleted.'
  );
}
