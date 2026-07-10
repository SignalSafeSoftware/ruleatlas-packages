type DiscoveryRowToggleProps = {
  expanded: boolean;
  onToggle: () => void;
  label: string;
  testId: string;
};

export function DiscoveryRowToggle({
  expanded,
  onToggle,
  label,
  testId,
}: Readonly<DiscoveryRowToggleProps>): React.ReactElement {
  return (
    <button
      type="button"
      className="btn ruleatlas-icon-btn discovery-directory-toggle"
      aria-expanded={expanded}
      aria-label={expanded ? `Collapse ${label}` : `Expand ${label}`}
      title={expanded ? `Collapse ${label}` : `Expand ${label}`}
      onClick={onToggle}
      data-testid={testId}
    >
      <i className={`bi ${expanded ? 'bi-chevron-down' : 'bi-chevron-right'}`} aria-hidden="true" />
    </button>
  );
}

export function DiscoveryRowToggleSpacer(): React.ReactElement {
  return <span className="discovery-directory-toggle-spacer" aria-hidden="true" />;
}
