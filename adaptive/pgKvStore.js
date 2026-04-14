const { Pool } = require('pg');

class PgKvStore {
  constructor(pool) {
    this.pool = pool;
    this._initialized = false;
  }

  async _ensureTable() {
    if (this._initialized) return;
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS kv_store (
        key TEXT PRIMARY KEY,
        value JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
    `);
    this._initialized = true;
  }

  async set(key, value) {
    await this._ensureTable();
    await this.pool.query(
      `INSERT INTO kv_store (key, value) VALUES ($1, $2::jsonb)
       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value`,
      [key, JSON.stringify(value)]
    );
  }

  async get(key) {
    await this._ensureTable();
    const result = await this.pool.query(
      'SELECT value FROM kv_store WHERE key = $1',
      [key]
    );
    if (result.rows.length === 0) return { value: null };
    return { value: result.rows[0].value };
  }

  async delete(key) {
    await this._ensureTable();
    await this.pool.query('DELETE FROM kv_store WHERE key = $1', [key]);
  }

  async list(prefix) {
    await this._ensureTable();
    let result;
    if (prefix) {
      result = await this.pool.query(
        'SELECT key FROM kv_store WHERE key LIKE $1 ORDER BY key',
        [prefix + '%']
      );
    } else {
      result = await this.pool.query('SELECT key FROM kv_store ORDER BY key');
    }
    return { value: result.rows.map(r => r.key) };
  }
}

module.exports = PgKvStore;
