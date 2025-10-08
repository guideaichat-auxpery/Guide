const express = require('express');
const cors = require('cors');
const Client = require('@replit/database');
const OpenAI = require('openai');
const { Pool } = require('pg');
require('dotenv').config();

const AdaptiveCore = require('./adaptiveCore');
const createAnalyticsRouter = require('./analyticsRoute');

const app = express();
const PORT = process.env.ADAPTIVE_PORT || 3000;

app.use(cors());
app.use(express.json());

// Centralized database and service instances
const kvDatabase = new Client();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const db = new Pool({ connectionString: process.env.DATABASE_URL });

// Initialize adaptive core with shared instances
const adaptiveCore = new AdaptiveCore(db, openai, kvDatabase);

app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'Guide Adaptive Learning System',
    timestamp: new Date().toISOString()
  });
});

app.post('/api/generate', async (req, res) => {
  try {
    const { query, context } = req.body;
    
    if (!query) {
      return res.status(400).json({
        success: false,
        error: 'Query parameter required'
      });
    }
    
    const result = await adaptiveCore.generateResponse(query, context || {});
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/feedback', async (req, res) => {
  try {
    const { interactionId, emoji } = req.body;
    
    if (!interactionId || !emoji) {
      return res.status(400).json({
        success: false,
        error: 'interactionId and emoji required'
      });
    }
    
    await adaptiveCore.recordFeedback(interactionId, emoji);
    
    res.json({
      success: true,
      message: 'Feedback recorded successfully'
    });
  } catch (error) {
    console.error('Feedback error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/simple-feedback', async (req, res) => {
  try {
    const { subject, rating, studentId } = req.body;
    
    if (!subject || rating === undefined) {
      return res.status(400).json({
        success: false,
        error: 'subject and rating required'
      });
    }
    
    if (rating < 1 || rating > 5 || !Number.isInteger(rating)) {
      return res.status(400).json({
        success: false,
        error: 'rating must be an integer between 1 and 5'
      });
    }
    
    const emojiMap = {
      1: '😕',
      2: '🤔', 
      3: '👍',
      4: '🤩',
      5: '🌟'
    };
    
    const result = await db.query(`
      SELECT id FROM adaptive_interactions 
      WHERE subject = $1 
      ${studentId ? 'AND student_id = $2' : ''}
      ORDER BY created_at DESC 
      LIMIT 1
    `, studentId ? [subject, studentId] : [subject]);
    
    if (!result.rows[0]) {
      return res.status(404).json({
        success: false,
        error: 'No interaction found for the given subject/student'
      });
    }
    
    const interactionId = result.rows[0].id;
    const emoji = emojiMap[rating];
    
    await db.query(`
      INSERT INTO adaptive_feedback (
        interaction_id, emoji, sentiment, weight, category, created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
    `, [
      interactionId,
      emoji,
      `rating_${rating}`,
      rating / 5.0,
      'simplified_rating'
    ]);
    
    res.json({
      success: true,
      message: 'Simplified feedback recorded',
      interactionId,
      rating,
      emoji
    });
  } catch (error) {
    console.error('Simple feedback error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/message', async (req, res) => {
  try {
    const { query, subject, yearLevel, studentId } = req.body;
    
    if (!query || !subject) {
      return res.status(400).json({
        success: false,
        error: 'query and subject required'
      });
    }
    
    const systemPrompt = await adaptiveCore.promptManager.getAdaptivePrompt(subject, yearLevel);
    
    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: query }
      ],
      temperature: 0.7,
      max_tokens: 800
    });
    
    const answer = response.choices[0].message.content;
    
    await adaptiveCore.semanticLogger.logInteraction({
      query,
      response: answer,
      subject,
      yearLevel,
      studentId
    });
    
    res.json({
      success: true,
      answer,
      systemPrompt: systemPrompt.substring(0, 100) + '...'
    });
  } catch (error) {
    console.error('Message error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/kv-feedback', async (req, res) => {
  try {
    const { subject, rating } = req.body;
    
    if (!subject || !rating) {
      return res.status(400).json({
        success: false,
        error: 'subject and rating required'
      });
    }
    
    const key = await adaptiveCore.feedbackSystem.recordFeedback(subject, rating);
    res.json({ 
      success: true, 
      key,
      message: 'Feedback stored in KV, will sync to PostgreSQL automatically'
    });
  } catch (error) {
    console.error('KV feedback error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/kv-store', async (req, res) => {
  try {
    const store = await adaptiveCore.feedbackSystem.getKVStore();
    res.json({ 
      success: true, 
      ...store
    });
  } catch (error) {
    console.error('KV store error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/kv-sync', async (req, res) => {
  try {
    const result = await adaptiveCore.feedbackSystem.syncKVtoPostgreSQL();
    res.json({ 
      success: true, 
      ...result
    });
  } catch (error) {
    console.error('KV sync error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/kv-embeddings', async (req, res) => {
  try {
    const store = await adaptiveCore.semanticLogger.getKVStore();
    res.json({ 
      success: true, 
      ...store
    });
  } catch (error) {
    console.error('KV embeddings error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/kv-embeddings-sync', async (req, res) => {
  try {
    const result = await adaptiveCore.semanticLogger.syncKVtoPostgreSQL();
    res.json({ 
      success: true, 
      ...result
    });
  } catch (error) {
    console.error('KV embeddings sync error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/trending/record', async (req, res) => {
  try {
    const { subject, keyword, sessionId, studentId } = req.body;
    
    if (!subject || !keyword) {
      return res.status(400).json({
        success: false,
        error: 'subject and keyword required'
      });
    }
    
    const key = await adaptiveCore.trendingKeywords.recordKeyword(subject, keyword, sessionId, studentId);
    res.json({ 
      success: true, 
      key,
      message: 'Keyword stored in KV, will sync to PostgreSQL automatically'
    });
  } catch (error) {
    console.error('Trending keyword record error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/trending/kv-store', async (req, res) => {
  try {
    const store = await adaptiveCore.trendingKeywords.getKVStore();
    res.json({ 
      success: true, 
      ...store
    });
  } catch (error) {
    console.error('Trending KV store error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/trending/kv-sync', async (req, res) => {
  try {
    const result = await adaptiveCore.trendingKeywords.syncKVtoPostgreSQL();
    res.json({ 
      success: true, 
      ...result
    });
  } catch (error) {
    console.error('Trending KV sync error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/trending/subject/:subject', async (req, res) => {
  try {
    const { subject } = req.params;
    const limit = parseInt(req.query.limit) || 10;
    
    const trending = await adaptiveCore.trendingKeywords.getTrendingBySubject(subject, limit);
    const weight = await adaptiveCore.trendingKeywords.getSubjectWeight(subject);
    
    res.json({ 
      success: true, 
      subject,
      trending,
      weight,
      count: trending.length
    });
  } catch (error) {
    console.error('Trending subject error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/trending/all', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    
    const result = await db.query(`
      SELECT subject, keyword, count, last_detected 
      FROM trending_keywords 
      ORDER BY count DESC, last_detected DESC 
      LIMIT $1
    `, [limit]);
    
    res.json({ 
      success: true, 
      trending: result.rows,
      count: result.rows.length
    });
  } catch (error) {
    console.error('All trending error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/trending/stats', async (req, res) => {
  try {
    const result = await db.query(`
      SELECT 
        subject,
        COUNT(DISTINCT keyword) as unique_keywords,
        SUM(count) as total_detections,
        MAX(last_detected) as most_recent
      FROM trending_keywords
      GROUP BY subject
      ORDER BY total_detections DESC
    `);
    
    res.json({ 
      success: true, 
      stats: result.rows
    });
  } catch (error) {
    console.error('Trending stats error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/trending/keyword/:keyword', async (req, res) => {
  try {
    const { keyword } = req.params;
    
    const result = await db.query(`
      SELECT * FROM trending_keywords 
      WHERE keyword = $1 
      ORDER BY last_detected DESC
    `, [keyword]);
    
    res.json({ 
      success: true, 
      keyword,
      history: result.rows
    });
  } catch (error) {
    console.error('Keyword history error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/weights/:subject?', async (req, res) => {
  try {
    const { subject } = req.params;
    const weights = await adaptiveCore.subjectCalibrator.getSubjectWeights(subject);
    
    res.json({ 
      success: true, 
      subject: subject || 'default',
      weights
    });
  } catch (error) {
    console.error('Weights error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/api/weights/:subject', async (req, res) => {
  try {
    const { subject } = req.params;
    const { weights } = req.body;
    
    await adaptiveCore.subjectCalibrator.updateWeights(subject, weights);
    
    res.json({ 
      success: true, 
      message: 'Weights updated successfully',
      subject,
      weights
    });
  } catch (error) {
    console.error('Update weights error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

const analyticsRouter = createAnalyticsRouter(db);
app.use('/api/analytics', analyticsRouter);

async function initializeDatabase() {
  try {
    await db.query(`
      CREATE TABLE IF NOT EXISTS adaptive_interactions (
        id SERIAL PRIMARY KEY,
        student_id VARCHAR(255),
        query_text TEXT NOT NULL,
        response_text TEXT,
        query_embedding TEXT,
        response_embedding TEXT,
        subject VARCHAR(100),
        year_level VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      CREATE TABLE IF NOT EXISTS adaptive_feedback (
        id SERIAL PRIMARY KEY,
        interaction_id INTEGER REFERENCES adaptive_interactions(id),
        emoji VARCHAR(10),
        sentiment VARCHAR(50),
        weight DECIMAL(3,2),
        category VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      CREATE TABLE IF NOT EXISTS adaptive_prompts (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(100),
        prompt_text TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        feedback_summary TEXT,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      CREATE TABLE IF NOT EXISTS adaptive_weights (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(100) UNIQUE,
        montessori_weight DECIMAL(3,2) DEFAULT 0.7,
        curriculum_weight DECIMAL(3,2) DEFAULT 0.6,
        scaffolding_weight DECIMAL(3,2) DEFAULT 0.5,
        complexity_weight DECIMAL(3,2) DEFAULT 0.6,
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      CREATE TABLE IF NOT EXISTS trending_keywords (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(100) NOT NULL,
        keyword VARCHAR(255) NOT NULL,
        count INTEGER DEFAULT 1,
        session_id VARCHAR(255),
        student_id VARCHAR(255),
        last_detected TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      CREATE INDEX IF NOT EXISTS idx_trending_subject_keyword 
      ON trending_keywords(subject, keyword)
    `);

    await db.query(`
      CREATE TABLE IF NOT EXISTS system_config (
        id SERIAL PRIMARY KEY,
        config_key VARCHAR(100) UNIQUE NOT NULL,
        config_value TEXT,
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await db.query(`
      INSERT INTO system_config (config_key, config_value, updated_at)
      VALUES ('last_refresh', NOW()::text, NOW())
      ON CONFLICT (config_key) DO NOTHING
    `);

    console.log('✅ Database tables initialized successfully');
  } catch (error) {
    console.error('❌ Database initialization error:', error);
    throw error;
  }
}

async function runAutoRefreshCycle() {
  try {
    const result = await db.query(`
      SELECT config_value as updated_at 
      FROM system_config 
      WHERE config_key = 'last_refresh'
    `);
    
    const now = Date.now();
    const lastRun = result.rows[0]?.updated_at;
    const REFRESH_INTERVAL = 72 * 60 * 60 * 1000;
    
    if (!lastRun || now - new Date(lastRun).getTime() > REFRESH_INTERVAL) {
      console.log('🔄 Running 72-hour auto-refresh cycle...');
      
      const { prompt, stats } = await adaptiveCore.promptManager.refreshSystemPromptWithHelpfulness();
      
      console.log('   📊 Helpfulness stats:');
      for (const [subject, data] of Object.entries(stats)) {
        const percentage = (data.ratio * 100).toFixed(1);
        console.log(`      ${subject}: ${percentage}% helpful (${data.helpful}/${data.total})`);
      }
      
      console.log('   ✨ Dynamic prompt updated');
      
      const subjectsResult = await db.query(`
        SELECT DISTINCT subject 
        FROM adaptive_interactions 
        WHERE subject IS NOT NULL 
          AND created_at > NOW() - interval '30 days'
        UNION
        SELECT DISTINCT subject 
        FROM adaptive_weights 
        WHERE subject IS NOT NULL
      `);
      
      const subjects = subjectsResult.rows.map(row => row.subject);
      
      if (subjects.length === 0) {
        console.log('   No subjects found with recent activity');
      }
      
      for (const subject of subjects) {
        const feedback = await adaptiveCore.promptManager.getRecentFeedback(subject);
        
        if (feedback.needsUpdate) {
          console.log(`   Refreshing ${subject} prompt based on feedback patterns...`);
          await adaptiveCore.promptManager.updatePromptFromFeedback(subject, feedback);
        }
      }
      
      console.log('✅ Auto-refresh cycle completed');
    } else {
      const hoursRemaining = Math.ceil((REFRESH_INTERVAL - (now - new Date(lastRun).getTime())) / (60 * 60 * 1000));
      console.log(`⏰ Next auto-refresh in ~${hoursRemaining} hours`);
    }
  } catch (error) {
    console.error('❌ Auto-refresh cycle error:', error.message);
  }
}

app.get("/analytics", async (req, res) => {
  try {
    const { value: keys } = await kvDatabase.list();
    const feedback = await Promise.all(
      keys.filter(k => k.startsWith("feedback_")).map(k => kvDatabase.get(k))
    );
    const embeddings = await Promise.all(
      keys.filter(k => k.startsWith("embedding_")).map(k => kvDatabase.get(k))
    );
    const trending = await Promise.all(
      keys.filter(k => k.startsWith("trending_")).map(k => kvDatabase.get(k))
    );
    res.json({ 
      success: true, 
      feedback, 
      embeddings,
      trending,
      totalKeys: keys.length
    });
  } catch (error) {
    console.error('Analytics KV error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.listen(PORT, async () => {
  console.log(`\n🚀 Guide Adaptive Learning System running on port ${PORT}`);
  console.log(`📊 Analytics dashboard: http://localhost:${PORT}/api/analytics/dashboard`);
  console.log(`💚 Health check: http://localhost:${PORT}/health\n`);
  
  await initializeDatabase();
  await runAutoRefreshCycle();
  
  setInterval(runAutoRefreshCycle, 60 * 60 * 1000);
});

module.exports = app;
