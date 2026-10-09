/**
 * Generates `shared/src/schema/product-card.gen.ts` (zod) from `data/product-card.schema.json`.
 * The JSON schema in the repo stays the single source of truth; this file is derived.
 *
 *   tsx shared/scripts/gen-product-card-schema.ts          write the generated file
 *   tsx shared/scripts/gen-product-card-schema.ts --check  fail if it is out of date (used by typecheck/CI)
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(here, '../../..');
const SRC = resolve(REPO, 'data/product-card.schema.json');
const OUT = resolve(here, '../src/schema/product-card.gen.ts');

type JsonSchema = {
  type?: string | string[];
  enum?: (string | number | null)[];
  pattern?: string;
  minimum?: number;
  maximum?: number;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  additionalProperties?: boolean | JsonSchema;
  items?: JsonSchema;
  description?: string;
  title?: string;
};

function lit(v: string | number | null): string {
  return v === null ? 'z.null()' : `z.literal(${JSON.stringify(v)})`;
}

function emit(s: JsonSchema, indent: string): string {
  const next = indent + '  ';
  let out: string;
  if (s.enum) {
    const nonNull = s.enum.filter((v): v is string | number => v !== null);
    const hasNull = s.enum.includes(null);
    const allStrings = nonNull.every((v) => typeof v === 'string');
    out = allStrings && nonNull.length > 0 ? `z.enum(${JSON.stringify(nonNull)})` : `z.union([${nonNull.map(lit).join(', ')}])`;
    if (hasNull) out += '.nullable()';
    return withDescription(out, s);
  }
  const types = Array.isArray(s.type) ? s.type : s.type ? [s.type] : [];
  const nullable = types.includes('null');
  const base = types.filter((t) => t !== 'null');
  if (base.length !== 1) {
    out = base.length === 0 ? 'z.unknown()' : `z.union([${base.map((t) => emit({ ...s, type: t, description: undefined }, indent)).join(', ')}])`;
  } else {
    const t = base[0];
    switch (t) {
      case 'string':
        out = 'z.string()';
        if (s.pattern) out += `.regex(new RegExp(${JSON.stringify(s.pattern)}))`;
        break;
      case 'number':
      case 'integer':
        out = t === 'integer' ? 'z.number().int()' : 'z.number()';
        if (s.minimum !== undefined) out += `.min(${s.minimum})`;
        if (s.maximum !== undefined) out += `.max(${s.maximum})`;
        break;
      case 'boolean':
        out = 'z.boolean()';
        break;
      case 'array':
        out = `z.array(${s.items ? emit(s.items, indent) : 'z.unknown()'})`;
        break;
      case 'object': {
        const props = s.properties ?? {};
        const req = new Set(s.required ?? []);
        const keys = Object.keys(props);
        if (keys.length === 0 && s.additionalProperties && typeof s.additionalProperties === 'object') {
          out = `z.record(z.string(), ${emit(s.additionalProperties, indent)})`;
          break;
        }
        const fields = keys
          .map((k) => {
            const p = props[k] as JsonSchema;
            const v = emit(p, next) + (req.has(k) ? '' : '.optional()');
            return `${next}${JSON.stringify(k)}: ${v},`;
          })
          .join('\n');
        const ctor = s.additionalProperties === false ? 'z.strictObject' : 'z.looseObject';
        out = `${ctor}({\n${fields}\n${indent}})`;
        if (s.additionalProperties && typeof s.additionalProperties === 'object') {
          out = `z.object({\n${fields}\n${indent}}).catchall(${emit(s.additionalProperties, indent)})`;
        }
        break;
      }
      default:
        out = 'z.unknown()';
    }
  }
  if (nullable) out += '.nullable()';
  return withDescription(out, s);
}

function withDescription(code: string, s: JsonSchema): string {
  return s.description ? `${code}.describe(${JSON.stringify(s.description)})` : code;
}

export function generate(): string {
  const schema = JSON.parse(readFileSync(SRC, 'utf8')) as JsonSchema;
  return [
    '// GENERATED FILE. Do not edit by hand.',
    '// Source: data/product-card.schema.json  ·  Generator: shared/scripts/gen-product-card-schema.ts',
    "import { z } from 'zod';",
    '',
    `export const ProductCardSchema = ${emit(schema, '')};`,
    '',
    'export type ProductCard = z.infer<typeof ProductCardSchema>;',
    '',
  ].join('\n');
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const code = generate();
  if (process.argv.includes('--check')) {
    const current = existsSync(OUT) ? readFileSync(OUT, 'utf8') : '';
    if (current !== code) {
      console.error('product-card.gen.ts is out of date. Run: npm run gen:schema');
      process.exit(1);
    }
    console.log('product-card.gen.ts is up to date');
  } else {
    writeFileSync(OUT, code);
    console.log('wrote', OUT);
  }
}
