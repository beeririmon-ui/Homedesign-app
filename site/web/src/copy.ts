/**
 * S18: the lines that could promise the customer an email (master-designer's words, site/copy/promises.he.json), as this
 * build shows them. tools/build-copy.ts chose them from EMAIL_PROVIDER: the wording without an email while no provider
 * sends what a line needs (today), the email wording once one does (S20 ת62). Only the chosen lines are in the bundle.
 * S20 (ת61): the shop's contact details (CONTACT_EMAIL, CONTACT_PHONE), or null while the owner has not decided; the
 * lines that offer contact were chosen by them too.
 */
import generated from '@generated/copy.he.json';
import type { Contact } from '@hd/shared/contact';

export type CopyKey = keyof typeof generated.strings;
const lines = generated.strings as Record<CopyKey, string | null>;

/** The line in this build's wording; null when it is not shown (the line, or the control it belongs to). */
export const copyHe = (key: CopyKey): string | null => lines[key];

/** The shop's contact details in this build, or null (the contact block is then not shown). */
export const contact = (generated as { contact: Contact | null }).contact;
