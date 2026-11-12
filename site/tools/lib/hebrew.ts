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
  // "הדפס", and a canvas the card does not call a print is "קנבס" (a flat canvas print never claims a texture).
  // S19 (QA ה8): and the texture word stands in a clause with no negation word (`claimsTexture`, read in materialHe)
  [/\b(?:print(?:ed)?|painting)\b/i, 'הדפס במרקם'],
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
const NEGATED_TEXTURE =
  /\b(?:non|un)[-\s]?(?:textured?|embossed)\b|\b(?:no|not|without|zero|free of)\s+(?:any\s+|a\s+)?(?:raised\s+)?(?:textures?|textured|embossing|embossed)\b/gi;

/**
 * S19, QA ה8: the safer default. A texture word ("embossed", "textured", "texture", "embossing") is a claim only in a
 * clause with no negation word in it. QA's ten denials the S17 pattern did not know ("no raised or embossed texture",
 * "neither textured nor embossed", "isn't textured", "texture: none", "texture-free", "lacks texture"…) all carry one.
 * A clause ends at a comma, a semicolon, a full stop, a slash, a bracket or a dash between spaces; not at a colon
 * ("texture: none" is one clause). So "textured print, no gloss" keeps its texture, and "non-slip textured print" loses
 * it: when a clause both claims and denies, the shop says the less.
 */
export const TEXTURE_WORD = /\b(?:embossed|embossing|textured?|textures)\b/i;
/**
 * S21, QA ה14: also the apostrophe-less contractions ("isnt", "doesnt", "dont"…) and a texture word with "-less" on it
 * ("texture-less", "textureless").
 */
export const NEGATION_WORD =
  /\b(?:no|not|non|none|never|neither|nor|without|lacks?|lacking|zero|free|minus|isnt|arent|wasnt|werent|doesnt|dont|didnt|hasnt|havent|hadnt)\b|\bun[-\s]?(?=textur|emboss)|\b(?:textur|emboss)[a-z]*[-‐‑]?less\b|n['’]t\b|(?:^|[^\u0590-\u05ff])(?:לא|ללא|בלי|אין|אינו|אינה)(?=$|[^\u0590-\u05ff])/i;
const CLAUSE = /[,;.!?()[\]{}/|·•]+|\s[-–—]+\s/;
/**
 * S21, QA ה14: denials written as a spec sheet writes them, read before the text is cut into clauses (a "/" or a "?" in
 * them would cut them apart): "w/o" is "without", and a texture word given a value that denies it ("Texture: N/A",
 * "Texture: Smooth", "texture: flat", "Embossed: N", "Textured: False", "(texture? no)") is "no texture".
 */
const WITHOUT_ABBR = /\bw\/o\b/gi;
const DENIED_VALUE = /\b(?:embossed|embossing|textured?|textures)\s*[:=?]\s*(?:n\/a|na|none|nil|no|n|false|smooth|flat|0|-)(?![\p{L}\p{N}/])/giu;
export const readDenials = (raw: string): string => raw.replace(WITHOUT_ABBR, 'without').replace(DENIED_VALUE, 'no texture');
/** the clauses of a material text that claim a texture (none: the text claims none) */
export function textureClauses(raw: string): string[] {
  return readDenials(raw.replace(HEDGED, ' '))
    .split(CLAUSE)
    .map((c) => c.trim())
    .filter((c) => TEXTURE_WORD.test(c) && !NEGATION_WORD.test(c));
}
export const claimsTexture = (raw: string): boolean => textureClauses(raw).length > 0;

/**
 * S17, QA ה5: a value that says it is unknown ("לא צוין", "חומר לא צוין", "לא ידוע", "unknown") is not a value: the
 * field is not shown. A rule for every product (tools/lib/public-text.ts `unknownPublicText` checks the catalog).
 */
export const UNKNOWN_VALUE =
  /^(?:(?:ה?חומר|ערך|צבע|מידה|מידות)\s+)?(?:לא\s+(?:צוין|מצוין|צויין|ידוע|ידועה|ברור|ברורה|מוגדר|הוגדר)|אינו\s+ידוע|לא\s+ידוע\s+עדיין)\.?$|^(?:unknown|n\/?a|not stated|not specified|unspecified|tbd|\?+|[-–—]+)$/i;
export const isUnknownValue = (s: string | null | undefined): boolean => !s || !s.trim() || UNKNOWN_VALUE.test(s.trim());

export function materialHe(raw: string): string | null {
  const text = raw.replace(HEDGED, ' ').replace(NEGATED_TEXTURE, ' ');
  // S19 (ה8): "הדפס במרקם" only when a clause claims the texture with no negation word in it
  for (const [re, he] of MATERIALS) if (re.test(text) && (he !== 'הדפס במרקם' || claimsTexture(raw))) return he;
  const paren = text.match(/\(([^)]*[֐-׿][^)]*)\)/);
  const he = paren?.[1]?.trim() ?? null;
  return isUnknownValue(he) ? null : he;
}

/** S19 (QA ה8): the material texts of a card that read as "הדפס במרקם", for the build's list */
export const textureClaimSources = (list: string[]): string[] => list.filter((m) => materialHe(m) === 'הדפס במרקם');

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
