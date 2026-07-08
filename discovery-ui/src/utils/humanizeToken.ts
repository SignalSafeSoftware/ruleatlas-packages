/** Convert snake_case tokens to Title Case for display. */
export function humanizeToken(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

/** Convert snake_case tokens to spaced lowercase (no title casing). */
export function humanizeTokenLower(value: string): string {
  return value.replace(/_/g, ' ');
}
