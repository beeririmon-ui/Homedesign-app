/** Price display, Design Bible ("₪ 1,290"): shekel sign, a space, thousands separator, no agorot when whole. */
export function formatIls(agorot: number): string {
  const whole = agorot % 100 === 0;
  const n = (agorot / 100).toLocaleString('en-US', {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  });
  // U+2066/U+2069 isolate the number so the shekel sign stays on the correct side in RTL text.
  return `₪ ⁦${n}⁩`;
}

/** Plain-text version for aria-label and JSON-LD contexts. */
export function ilsNumber(agorot: number): string {
  return (agorot / 100).toFixed(2);
}
