const integerFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

const compactFormatter = new Intl.NumberFormat(undefined, {
  notation: 'compact',
  maximumFractionDigits: 1,
});

/** Format integer counts with locale-aware thousands separators. */
export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }
  return integerFormatter.format(value);
}

/** Compact label for tight chart space (e.g. 151.1K). Use title/tooltip with formatInteger for exact value. */
export function formatCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }
  if (Math.abs(value) < 10_000) {
    return formatInteger(value);
  }
  return compactFormatter.format(value);
}

/** Percent share; returns — when total is missing/zero. Zero part renders as 0.0%. */
export function formatPercent(part: number | undefined, total: number | undefined): string {
  if (total === null || total === undefined || !Number.isFinite(total) || total === 0) {
    return '—';
  }
  const numerator = part ?? 0;
  if (!Number.isFinite(numerator)) {
    return '—';
  }
  return `${((numerator / total) * 100).toFixed(1)}%`;
}

/** Summary card / mixed display: numbers get commas; strings pass through. */
export function formatMetricValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'number') {
    return formatInteger(value);
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return '—';
  }
  return trimmed;
}
