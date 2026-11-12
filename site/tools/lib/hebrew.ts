/**
 * Provisional Hebrew display text derived from product cards, until real copy exists.
 * Product cards hold supplier (English) names; every derived name is flagged `name_provisional`.
 */

const MATERIALS: [RegExp, string][] = [
  [/travertine|cave stone|dolomite/i, 'טרוורטין'],
  [/seagrass/i, 'קש ים'],
  [/jute/i, 'יוטה'],
  [/cotton rope/i, 'חבל כותנה'],
  [/macrame/i, 'מקרמה'],
  [/wool/i, 'צמר'],
  [/hemp|linen/i, 'פשתן'],
  [/boucle|teddy/i, 'בוקלה'],
  [/corduroy/i, 'קורדרוי'],
  [/chenille/i, 'שניל'],
  [/felt/i, 'לבד'],
  [/silk/i, 'משי'],
  [/stoneware|ceramic|pottery/i, 'קרמיקה'],
  [/cement/i, 'מלט'],
  [/cotton/i, 'כותנה'],
  [/polyester/i, 'אריג סינתטי'],
  // S15 (master-designer §5): "במרקם" only when the card says the print is embossed or textured; any other print is
  // "הדפס", and a canvas the card does not call a print is "קנבס" (a flat canvas print never claims a texture)
  [/^(?=.*\b(?:print(?:ed)?|painting)\b)(?=.*\b(?:embossed|textured?)\b)/i, 'הדפס במרקם'],
  [/\bprint(?:ed)?\b/i, 'הדפס'],
  [/\bcanvas\b/i, 'קנבס'],
  [/iron|metal|steel/i, 'מתכת'],
  [/wood|oak|beech/i, 'עץ'],
  [/fabric|cloth/i, 'בד'],
];

/**
 * S15: a guess the card hedges ("(material not stated - possibly PVC/printed)") is not a claim the shop makes: the
 * hedged part is left out before the material is read.
 */
const HEDGED = /\([^)]*\b(?:possibly|probably|perhaps|maybe|likely|not stated|unclear|unknown|unverified)\b[^)]*\)/gi;

/**
 * S17, QA ה3: a texture the card denies is no texture: "non-textured print", "smooth print (no texture)", "without
 * embossing" are a print, never "הדפס במרקם". The denied phrase is left out before the material is read.
 */
const NEGATED_TEXTURE = /\b(?:non|un)[-\s]?(?:textured?|embossed)\b|\b(?:no|not|without|zero|free of)\s+(?:any\s+|a\s+)?(?:raised\s+)?(?:textures?|textured|embossing|embossed)\b/gi;

/**
 * S17, QA ה5: a value that says it is unknown ("לא צוין", "חומר לא צוין", "לא ידוע", "unknown") is not a value: the
 * field is not shown. A rule for every product (tools/lib/public-text.ts `unknownPublicText` checks the catalog).
 */
export const UNKNOWN_VALUE = /^(?:(?:ה?חומר|ערך|צבע|מידה|מידות)\s+)?(?:לא\s+(?:צוין|מצוין|צויין|ידוע|ידועה|ברור|ברורה|מוגדר|הוגדר)|אינו\s+ידוע|לא\s+ידוע\s+עדיין)\.?$|^(?:unknown|n\/?a|not stated|not specified|unspecified|tbd|\?+|[-–—]+)$/i;
export const isUnknownValue = (s: string | null | undefined): boolean => !s || !s.trim() || UNKNOWN_VALUE.test(s.trim());

export function materialHe(raw: string): string | null {
  const text = raw.replace(HEDGED, ' ').replace(NEGATED_TEXTURE, ' ');
  for (const [re, he] of MATERIALS) if (re.test(text)) return he;
  const paren = text.match(/\(([^)]*[֐-׿][^)]*)\)/);
  const he = paren?.[1]?.trim() ?? null;
  return isUnknownValue(he) ? null : he;
}

export function materialsHe(list: string[]): string[] {
  return [...new Set(list.map(materialHe).filter((m): m is string => !isUnknownValue(m)))];
}

const ANCHORS: [string, string][] = [
  ['לבן חם', '#F4F1EC'],
  ['שיבולת שועל', '#E6DCCB'],
  ['אלון בהיר', '#C8A27A'],
  ['אפור ערפל', '#D9D6D0'],
  ['פחם', '#3A3A3A'],
  ['מרווה', '#A7B09A'],
  ['טבעי', '#B99B74'],
  ['חול', '#D6C3A5'],
];

function rgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function colorNameHe(hex: string): string {
  const [r, g, b] = rgb(hex);
  let best = ANCHORS[0]![0];
  let bestD = Infinity;
  for (const [name, h] of ANCHORS) {
    const [R, G, B] = rgb(h);
    const d = 2 * (r - R) ** 2 + 4 * (g - G) ** 2 + 3 * (b - B) ** 2;
    if (d < bestD) {
      bestD = d;
      best = name;
    }
  }
  return best;
}

export const hasHebrew = (s: string | null | undefined): boolean => !!s && /[֐-׿]/.test(s);
