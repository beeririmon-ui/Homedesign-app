/**
 * Draft cards (2026-11-03, SITE1): the AliExpress DS API writes a card with colors, visual_weight, dimensions and texture
 * left for the sourcing-agent to fill from the photos ("DRAFT from AliExpress DS API ... NOT filled"). Such a card is not
 * a schema violation to hide: it is unfinished sourcing work, reported by name by the build and the tests, and never shown
 * on the site until it is filled (the schema, a binding document, requires those fields).
 */
export const DRAFT_MARKER = 'DRAFT from AliExpress DS API';
/** the fields the DS API leaves empty, as zod issue paths */
export const DRAFT_FIELDS = ['colors.dominant_hex', 'colors.temperature', 'visual_weight'] as const;

type Raw = { notes?: unknown; colors?: unknown; visual_weight?: unknown };

/** True when the card carries the draft marker and its draft fields are the unfilled nulls. */
export function isDraftCard(raw: Raw): boolean {
  if (typeof raw.notes !== 'string' || !raw.notes.includes(DRAFT_MARKER)) return false;
  const colors = (raw.colors ?? {}) as { dominant_hex?: unknown; temperature?: unknown };
  return colors.dominant_hex == null && colors.temperature == null && raw.visual_weight == null;
}

/** True when every validation issue of a draft card is one of its unfilled draft fields. */
export function onlyDraftIssues(issuePaths: string[]): boolean {
  return issuePaths.length > 0 && issuePaths.every((p) => (DRAFT_FIELDS as readonly string[]).includes(p));
}
