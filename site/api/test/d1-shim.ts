/**
 * Minimal D1Database over node:sqlite for fast unit tests of the Worker routes.
 * The real thing (workerd + Miniflare D1) is exercised by the e2e suite through `wrangler dev`.
 */
import { DatabaseSync, type SQLInputValue } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

type Row = Record<string, unknown>;

class Stmt {
  constructor(
    private db: DatabaseSync,
    private sql: string,
    private args: SQLInputValue[] = [],
  ) {}
  bind(...args: unknown[]): Stmt {
    return new Stmt(this.db, this.sql, args.map((a) => (typeof a === 'boolean' ? (a ? 1 : 0) : (a as SQLInputValue))));
  }
  async first<T = Row>(col?: string): Promise<T | null> {
    const row = this.db.prepare(this.sql).get(...this.args) as Row | undefined;
    if (!row) return null;
    return (col ? row[col] : { ...row }) as T;
  }
  async all<T = Row>(): Promise<{ results: T[]; success: true; meta: Record<string, unknown> }> {
    const rows = this.db.prepare(this.sql).all(...this.args) as Row[];
    return { results: rows.map((r) => ({ ...r })) as T[], success: true, meta: {} };
  }
  async run(): Promise<{ success: true; meta: { changes: number; last_row_id: number } }> {
    const r = this.db.prepare(this.sql).run(...this.args);
    return { success: true, meta: { changes: Number(r.changes), last_row_id: Number(r.lastInsertRowid) } };
  }
  runSync() {
    return this.db.prepare(this.sql).run(...this.args);
  }
}

export function createD1(): D1Database {
  const db = new DatabaseSync(':memory:');
  db.exec('PRAGMA foreign_keys = ON;');
  const d1 = {
    prepare: (sql: string) => new Stmt(db, sql),
    async batch(stmts: Stmt[]) {
      db.exec('BEGIN');
      try {
        const out = [];
        for (const s of stmts) out.push(await s.run());
        db.exec('COMMIT');
        return out;
      } catch (e) {
        db.exec('ROLLBACK');
        throw e;
      }
    },
    async exec(sql: string) {
      db.exec(sql);
      return { count: 0, duration: 0 };
    },
    _raw: db,
  };
  return d1 as unknown as D1Database;
}

const here = dirname(fileURLToPath(import.meta.url));

/** Applies migrations and the seed SQL built from a catalog. */
export function migrate(d1: D1Database, seedSql?: string): void {
  const raw = (d1 as unknown as { _raw: DatabaseSync })._raw;
  raw.exec(readFileSync(resolve(here, '../migrations/0001_init.sql'), 'utf8'));
  if (seedSql) raw.exec(seedSql.replace('PRAGMA defer_foreign_keys = ON;', ''));
}
