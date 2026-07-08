/** Human-readable file size from discovery inventory `size_bytes` (missing/invalid → 0 B). */
export function formatBytes(size: number | null | undefined): string {
  const bytes = typeof size === 'number' && Number.isFinite(size) && size >= 0 ? size : 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** Raw byte value for sorting/aggregation; missing or invalid inventory size → 0. */
export function sizeBytesValue(size: number | null | undefined): number {
  return typeof size === 'number' && Number.isFinite(size) && size >= 0 ? size : 0;
}
