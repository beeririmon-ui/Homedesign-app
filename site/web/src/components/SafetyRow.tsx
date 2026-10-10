/**
 * "תקנים ובטיחות" (D9): the card's standards and safety claims, as a row of the product's spec list. Nothing is shown
 * for a product without them, and nothing the card does not state (shared/src/safety.ts).
 */
import type { PublicSafety } from '@hd/shared';
import { safetyLinesHe } from '@hd/shared/safety';

export function SafetyRow({ safety }: { safety: PublicSafety | null }) {
  const lines = safetyLinesHe(safety);
  if (!lines.length) return null;
  const anyVerified = safety!.certificates.some((c) => c.verified);
  return (
    <>
      <dt>תקנים ובטיחות</dt>
      <dd>
        <ul class="safety-list">
          {lines.map((l) => (
            <li key={l.text}>
              {l.href ? (
                <a href={l.href} rel="noopener noreferrer" target="_blank">
                  {l.text}
                  <span class="sr-only"> (נפתח בחלון חדש)</span>
                </a>
              ) : (
                l.text
              )}
            </li>
          ))}
        </ul>
        {anyVerified ? null : <span class="small muted">לפי הספק</span>}
      </dd>
    </>
  );
}
