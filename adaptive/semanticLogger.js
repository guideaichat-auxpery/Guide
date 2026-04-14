class SemanticLogger {
  constructor(db, openai, kvClient) {
    this.db = db;
    this.openai = openai;
    this.kvStore = kvClient;
    this.isSyncing = false;
    this.startAutoSync();
  }

  async logInteraction(data) {
    const { query, response, subject, yearLevel, studentId } = data;
    
    const crypto = require('crypto');
    const key = `embedding_${crypto.randomUUID()}`;
    
    const queryEmbedding = await this.generateEmbedding(query);
    const responseEmbedding = await this.generateEmbedding(response);
    
    await this.kvStore.set(key, {
      studentId,
      query,
      response,
      queryEmbedding,
      responseEmbedding,
      subject,
      yearLevel,
      timestamp: new Date().toISOString()
    });
    
    return key;
  }

  async syncKVtoPostgreSQL() {
    if (this.isSyncing) {
      const { value: allKeys } = await this.kvStore.list();
      const keys = allKeys.filter(k => k.startsWith("embedding_"));
      return { synced: 0, remaining: keys.length, message: 'Sync already in progress' };
    }

    const { value: allKeys } = await this.kvStore.list();
    const keys = allKeys.filter(k => k.startsWith("embedding_"));
    if (keys.length === 0) {
      return { synced: 0 };
    }

    this.isSyncing = true;

    try {
      let syncedCount = 0;

      for (const key of keys) {
        try {
          const kvResult = await this.kvStore.get(key);
          const data = kvResult?.value;
          if (!data) continue;

          await this.db.query(`
            INSERT INTO adaptive_interactions (
              student_id,
              query_text,
              response_text,
              query_embedding,
              response_embedding,
              subject,
              year_level,
              created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
          `, [
            data.studentId,
            data.query,
            data.response,
            JSON.stringify(data.queryEmbedding),
            JSON.stringify(data.responseEmbedding),
            data.subject,
            data.yearLevel,
            data.timestamp
          ]);

          await this.kvStore.delete(key);
          syncedCount++;
        } catch (error) {
          console.error(`Embedding sync error for ${key}:`, error.message);
        }
      }

      const { value: allRemainingKeys } = await this.kvStore.list();
      const remainingKeys = allRemainingKeys.filter(k => k.startsWith("embedding_"));
      return { synced: syncedCount, remaining: remainingKeys.length };
    } finally {
      this.isSyncing = false;
    }
  }

  startAutoSync() {
    setInterval(async () => {
      const result = await this.syncKVtoPostgreSQL();
      if (result.synced > 0) {
        console.log(`🔄 Synced ${result.synced} embedding entries to PostgreSQL`);
      }
    }, 30000);
  }

  async getKVStore() {
    const { value: allKeys } = await this.kvStore.list();
    const keys = allKeys.filter(k => k.startsWith("embedding_"));
    return {
      size: keys.length,
      keys: keys
    };
  }

  async generateEmbedding(text) {
    const response = await this.openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text
    });
    
    return response.data[0].embedding;
  }

  async findSimilarInteractions(queryText, subject = null, limit = 5) {
    const queryEmbedding = await this.generateEmbedding(queryText);
    
    const whereClause = subject ? 'WHERE subject = $2' : '';
    const params = subject ? [JSON.stringify(queryEmbedding), subject] : [JSON.stringify(queryEmbedding)];
    
    const result = await this.db.query(`
      SELECT 
        id,
        query_text,
        response_text,
        subject,
        year_level,
        (1 - (query_embedding::vector <=> $1::vector)) as similarity
      FROM adaptive_interactions
      ${whereClause}
      ORDER BY similarity DESC
      LIMIT ${limit}
    `, params);
    
    return result.rows;
  }

  async getTopTopics(subject = null, timeframe = '7 days') {
    const whereClause = subject 
      ? 'WHERE subject = $1 AND created_at > NOW() - $2::interval'
      : 'WHERE created_at > NOW() - $1::interval';
    
    const params = subject ? [subject, timeframe] : [timeframe];
    
    const result = await this.db.query(`
      SELECT 
        query_text,
        COUNT(*) as frequency,
        AVG((
          SELECT AVG(
            CASE 
              WHEN emoji IN ('🤩', '💡', '🌟') THEN 1.0
              WHEN emoji IN ('👍', '📚') THEN 0.7
              WHEN emoji IN ('😕', '🤔') THEN 0.3
              ELSE 0.5
            END
          )
          FROM adaptive_feedback
          WHERE adaptive_feedback.interaction_id = adaptive_interactions.id
        )) as sentiment
      FROM adaptive_interactions
      ${whereClause}
      GROUP BY query_text
      ORDER BY frequency DESC
      LIMIT 10
    `, params);
    
    return result.rows;
  }

  async clusterInteractions(subject, daysSince = 7) {
    const result = await this.db.query(`
      SELECT 
        id,
        query_text,
        response_text,
        query_embedding
      FROM adaptive_interactions
      WHERE subject = $1 
        AND created_at > NOW() - interval '${daysSince} days'
    `, [subject]);
    
    const clusters = this.kMeansClustering(result.rows, 5);
    
    return clusters;
  }

  kMeansClustering(dataPoints, k) {
    if (dataPoints.length < k) {
      return dataPoints.map((point, idx) => ({
        clusterId: idx,
        points: [point]
      }));
    }
    
    const centroids = this.initializeCentroids(dataPoints, k);
    let clusters = [];
    
    for (let iteration = 0; iteration < 10; iteration++) {
      clusters = this.assignToClusters(dataPoints, centroids);
      centroids = this.updateCentroids(clusters);
    }
    
    return clusters.map((cluster, idx) => ({
      clusterId: idx,
      centroid: centroids[idx],
      points: cluster,
      representativeQuery: this.findRepresentative(cluster)
    }));
  }

  initializeCentroids(dataPoints, k) {
    const shuffled = [...dataPoints].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, k).map(p => JSON.parse(p.query_embedding));
  }

  assignToClusters(dataPoints, centroids) {
    const clusters = centroids.map(() => []);
    
    dataPoints.forEach(point => {
      const embedding = JSON.parse(point.query_embedding);
      const distances = centroids.map(centroid => 
        this.cosineSimilarity(embedding, centroid)
      );
      const closestCluster = distances.indexOf(Math.max(...distances));
      clusters[closestCluster].push(point);
    });
    
    return clusters;
  }

  updateCentroids(clusters) {
    return clusters.map(cluster => {
      if (cluster.length === 0) return new Array(1536).fill(0);
      
      const embeddings = cluster.map(p => JSON.parse(p.query_embedding));
      const dimensions = embeddings[0].length;
      const centroid = new Array(dimensions).fill(0);
      
      embeddings.forEach(emb => {
        emb.forEach((val, idx) => {
          centroid[idx] += val / embeddings.length;
        });
      });
      
      return centroid;
    });
  }

  cosineSimilarity(vec1, vec2) {
    const dotProduct = vec1.reduce((sum, val, idx) => sum + val * vec2[idx], 0);
    const mag1 = Math.sqrt(vec1.reduce((sum, val) => sum + val * val, 0));
    const mag2 = Math.sqrt(vec2.reduce((sum, val) => sum + val * val, 0));
    
    return dotProduct / (mag1 * mag2);
  }

  findRepresentative(cluster) {
    if (cluster.length === 0) return null;
    return cluster.sort((a, b) => b.frequency - a.frequency)[0].query_text;
  }
}

module.exports = SemanticLogger;
