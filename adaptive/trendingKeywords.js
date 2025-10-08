const Client = require('@replit/database');

class TrendingKeywords {
  constructor(db, kvClient = null) {
    this.db = db;
    this.kvStore = kvClient || new Client();
    this.isSyncing = false;
    this.startAutoSync();
  }

  async recordKeyword(subject, keyword, sessionId = null, studentId = null) {
    const crypto = require('crypto');
    const key = `trending_${crypto.randomUUID()}`;
    
    await this.kvStore.set(key, {
      subject,
      keyword,
      sessionId,
      studentId,
      timestamp: new Date().toISOString()
    });
    
    return key;
  }

  async syncKVtoPostgreSQL() {
    if (this.isSyncing) {
      const { value: allKeys } = await this.kvStore.list();
      const keys = allKeys.filter(k => k.startsWith("trending_"));
      return { synced: 0, remaining: keys.length, message: 'Sync already in progress' };
    }

    const { value: allKeys } = await this.kvStore.list();
    const keys = allKeys.filter(k => k.startsWith("trending_"));
    if (keys.length === 0) {
      return { synced: 0 };
    }

    this.isSyncing = true;

    try {
      let syncedCount = 0;

      for (const key of keys) {
        try {
          const kvResult = await this.kvStore.get(key);
          if (!kvResult || !kvResult.value) continue;
          const data = kvResult.value;

          const existingResult = await this.db.query(`
            SELECT id, count FROM trending_keywords
            WHERE subject = $1 AND keyword = $2
            ORDER BY last_detected DESC
            LIMIT 1
          `, [data.subject, data.keyword]);

          if (existingResult.rows[0]) {
            await this.db.query(`
              UPDATE trending_keywords
              SET count = count + 1,
                  last_detected = $1
              WHERE id = $2
            `, [data.timestamp, existingResult.rows[0].id]);
          } else {
            await this.db.query(`
              INSERT INTO trending_keywords (
                subject, keyword, count, session_id, student_id, last_detected, created_at
              ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            `, [
              data.subject,
              data.keyword,
              1,
              data.sessionId,
              data.studentId,
              data.timestamp,
              data.timestamp
            ]);
          }

          await this.kvStore.delete(key);
          syncedCount++;
        } catch (error) {
          console.error(`Trending keyword sync error for ${key}:`, error.message);
        }
      }

      const { value: allRemainingKeys } = await this.kvStore.list();
      const remainingKeys = allRemainingKeys.filter(k => k.startsWith("trending_"));
      return { synced: syncedCount, remaining: remainingKeys.length };
    } finally {
      this.isSyncing = false;
    }
  }

  startAutoSync() {
    setInterval(async () => {
      const result = await this.syncKVtoPostgreSQL();
      if (result.synced > 0) {
        console.log(`🔄 Synced ${result.synced} trending keyword entries to PostgreSQL`);
      }
    }, 30000);
  }

  async getKVStore() {
    const { value: allKeys } = await this.kvStore.list();
    const keys = allKeys.filter(k => k.startsWith("trending_"));
    return {
      size: keys.length,
      keys: keys
    };
  }

  async getSubjectWeight(subject) {
    const trending = await this.getTrendingBySubject(subject);
    const total = trending.reduce((sum, item) => sum + item.count, 0);
    return Math.min(1.5, 1 + total / 50);
  }

  async getTrendingBySubject(subject, limit = 10) {
    const result = await this.db.query(`
      SELECT keyword, count, last_detected
      FROM trending_keywords
      WHERE subject = $1
      ORDER BY count DESC, last_detected DESC
      LIMIT $2
    `, [subject, limit]);

    return result.rows;
  }

  async getAllTrending(timeframe = '7 days', limit = 20) {
    const result = await this.db.query(`
      SELECT subject, keyword, count, last_detected
      FROM trending_keywords
      WHERE last_detected > NOW() - $1::interval
      ORDER BY count DESC, last_detected DESC
      LIMIT $2
    `, [timeframe, limit]);

    return result.rows;
  }

  async getTrendingStats(subject = null) {
    const whereClause = subject ? 'WHERE subject = $1' : '';
    const params = subject ? [subject] : [];

    const result = await this.db.query(`
      SELECT 
        subject,
        COUNT(DISTINCT keyword) as unique_keywords,
        SUM(count) as total_occurrences,
        MAX(last_detected) as most_recent
      FROM trending_keywords
      ${whereClause}
      GROUP BY subject
      ORDER BY total_occurrences DESC
    `, params);

    return result.rows;
  }

  async getKeywordHistory(keyword, subject = null, days = 30) {
    const whereClause = subject 
      ? 'WHERE keyword = $1 AND subject = $2 AND last_detected > NOW() - $3::interval'
      : 'WHERE keyword = $1 AND last_detected > NOW() - $2::interval';
    
    const params = subject 
      ? [keyword, subject, `${days} days`]
      : [keyword, `${days} days`];

    const result = await this.db.query(`
      SELECT 
        subject,
        keyword,
        count,
        last_detected,
        created_at
      FROM trending_keywords
      ${whereClause}
      ORDER BY last_detected DESC
    `, params);

    return result.rows;
  }
}

module.exports = TrendingKeywords;
