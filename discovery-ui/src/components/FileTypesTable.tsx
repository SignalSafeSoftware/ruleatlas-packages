import { humanizeToken } from '../utils/humanizeToken';
import type { FileTypesTableProps } from '../types/discovery';

export function FileTypeBadge({ language, displayType }: Readonly<{ language: string; displayType?: string }>): React.ReactElement {
  return (
    <span className="badge text-bg-secondary" title={displayType ?? language}>
      {language}
    </span>
  );
}

export function FileTypesTable({
  rows,
  emptyLabel = 'No file type mappings',
  testId = 'file-types-table',
  quickFilter = '',
  onQuickFilterChange,
  renderLanguageCell,
  renderInfoCell,
}: FileTypesTableProps): React.ReactElement {
  const query = quickFilter.trim().toLowerCase();
  const filtered = query
    ? rows.filter((row) =>
        [row.pattern, row.match_type, row.language, row.display_type, row.file_kind]
          .some((value) => String(value ?? '').toLowerCase().includes(query)),
      )
    : rows;

  return (
    <div className="card" data-testid={testId}>
      <div className="card-body">
        {onQuickFilterChange ? (
          <input
            type="search"
            className="form-control form-control-sm mb-3"
            placeholder="Filter mappings…"
            value={quickFilter}
            onChange={(event) => onQuickFilterChange(event.target.value)}
            data-testid={`${testId}-filter`}
          />
        ) : null}
        {filtered.length === 0 ? (
          <p className="small text-body-secondary mb-0">{emptyLabel}</p>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm table-striped table-hover ruleatlas-table mb-0">
              <thead>
                <tr>
                  <th>Pattern</th>
                  <th>Match</th>
                  <th>Language</th>
                  <th>Display type</th>
                  <th>Kind</th>
                  <th>Source</th>
                  <th>Enabled</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={`${row.match_type}:${row.pattern}`} data-testid={`${testId}-row-${row.pattern}`}>
                    <td>{row.pattern}</td>
                    <td>{humanizeToken(row.match_type)}</td>
                    <td>{renderLanguageCell ? renderLanguageCell(row) : row.language}</td>
                    <td>{row.display_type}</td>
                    <td>{humanizeToken(row.file_kind)}</td>
                    <td>{row.source === 'built_in' ? 'Built-in' : 'Custom'}</td>
                    <td>{row.enabled === false ? 'No' : 'Yes'}</td>
                    <td>{renderInfoCell ? renderInfoCell(row) : null}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
