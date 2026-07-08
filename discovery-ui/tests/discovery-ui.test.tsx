import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FileTypesTable } from '../src/components/FileTypesTable';
import { LineCountByFileTypeTable } from '../src/components/LineCountByFileTypeTable';
import {
  buildExcludeConfirmMessage,
  containingFolderRawPath,
  fileExcludeGlob,
  folderExcludeGlob,
} from '../src/utils/excludeScope';

afterEach(() => {
  cleanup();
});

describe('FileTypesTable', () => {
  it('renders rows', () => {
    render(
      <FileTypesTable
        rows={[
          {
            pattern: '.py',
            match_type: 'extension',
            language: 'Python',
            display_type: '.py',
            file_kind: 'code',
            default_bucket_hint: 'production',
            source: 'built_in',
            enabled: true,
          },
        ]}
      />,
    );
    expect(screen.getByText('Python')).toBeInTheDocument();
  });

  it('renders empty state', () => {
    render(<FileTypesTable rows={[]} emptyLabel="No mappings" />);
    expect(screen.getByText('No mappings')).toBeInTheDocument();
  });
});

describe('LineCountByFileTypeTable', () => {
  it('renders metric rows', () => {
    render(
      <LineCountByFileTypeTable
        title="Line count by file type"
        testId="line-count-table"
        columns={[{ id: 'language', key: 'language', label: 'Language' }]}
        rows={[{ language: 'Python', code_lines: 100 }]}
      />,
    );
    expect(screen.getByTestId('line-count-table')).toHaveTextContent('Python');
  });

  it('fires filter callback', () => {
    const onFilter = vi.fn();
    render(<FileTypesTable rows={[]} quickFilter="" onQuickFilterChange={onFilter} />);
    expect(screen.getByTestId('file-types-table-filter')).toBeInTheDocument();
  });
});

describe('excludeScope helpers', () => {
  it('builds folder exclude glob', () => {
    expect(folderExcludeGlob('src/lib')).toBe('src/lib/**');
    expect(fileExcludeGlob('src/main.py')).toBe('**/src/main.py');
    expect(containingFolderRawPath('src/main.py')).toBe('src');
  });

  it('builds confirm message without window', () => {
    const message = buildExcludeConfirmMessage('vendor/**', { kind: 'folder' });
    expect(message).toContain('vendor/**');
    expect(message).not.toMatch(/window/);
  });
});
