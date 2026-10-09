const LRI = String.fromCharCode(0x2066); // left-to-right isolate
const PDI = String.fromCharCode(0x2069); // pop directional isolate
const NBSP = String.fromCharCode(0x00a0);

/** Price display, Design Bible ("₪ 1,290"): shekel sign, a space, thousands separator, no agorot when whole. */
export function formatIls(agorot: number): string {
  const whole = agorot % 100 === 0;
  const n = (agorot / 100).toLocaleString('en-US', {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  });
  // LTR isolate: inside Hebrew text the price still reads "₪ 1,290" as written.
  return `${LRI}₪${NBSP}${n}${PDI}`;
}

/** Plain-text version for aria-label and JSON-LD contexts. */
export function ilsNumber(agorot: number): string {
  return (agorot / 100).toFixed(2);
}
