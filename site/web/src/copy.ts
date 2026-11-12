/**
 * S18: the lines that could promise the customer an email (master-designer's words, site/copy/promises.he.json), as this
 * build shows them. tools/build-copy.ts chose them from EMAIL_PROVIDER: the wording without an email while no provider
 * sends (today), the email wording once one does. Only the chosen lines are in the bundle.
 */
import generated from '@generated/copy.he.json';

export type CopyKey = keyof typeof generated.strings;
const lines = generated.strings as Record<CopyKey, string | null>;

/** The line in this build's wording; null when it is not shown (the line, or the control it belongs to). */
export const copyHe = (key: CopyKey): string | null => lines[key];
