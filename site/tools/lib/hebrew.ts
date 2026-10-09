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
  [/embossed|print|painting/i, 'הדפס במרקם'],
  [/iron|metal|steel/i, 'מתכת'],
  [/wood|oak|beech/i, 'עץ'],
  [/fabric|cloth/i, 'בד'],
];

export function materialHe(raw: string): string | null {
  for (const [re, he] of MATERIALS) if (re.test(raw)) return he;
  const paren = raw.match(/\(([^)]*[֐-׿][^)]*)\)/);
  return paren?.[1]?.trim() ?? null;
}

export function materialsHe(list: string[]): string[] {
  return [...new Set(list.map(materialHe).filter((m): m is string => !!m))];
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
