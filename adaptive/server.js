const express = require('express');
const cors = require('cors');
require('dotenv').config();

const AdaptiveCore = require('./adaptiveCore');
const createAnalyticsRouter = require('./analyticsRoute');

const app = express();
const PORT = process.env.ADAPTIVE_PORT || 3000;

app.use(cors());
app.use(express.json());

const adaptiveCore = new AdaptiveCore();

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

app.use('/api', createAnalyticsRouter(adaptiveCore));

app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: err.message
  });
});

async function initializeDatabase() {
  const { db } = adaptiveCore;
  
  try {
    await db.query(`
      CREATE TABLE IF NOT EXISTS adaptive_interactions (
        id SERIAL PRIMARY KEY,
        student_id VARCHAR(255),
        query_text TEXT NOT NULL,
        response_text TEXT NOT NULL,
        query_embedding JSONB,
        response_embedding JSONB,
        subject VARCHAR(100),
        year_level VARCHAR(20),
        created_at TIMESTAMP DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS adaptive_feedback (
        id SERIAL PRIMARY KEY,
        interaction_id INTEGER REFERENCES adaptive_interactions(id),
        emoji VARCHAR(10),
        sentiment VARCHAR(50),
        weight DECIMAL(3,2),
        category VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS adaptive_prompts (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(100),
        prompt_text TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS adaptive_weights (
        id SERIAL PRIMARY KEY,
        subject VARCHAR(100),
        montessori_weight DECIMAL(3,2),
        curriculum_weight DECIMAL(3,2),
        scaffolding_weight DECIMAL(3,2),
        complexity_level DECIMAL(3,2),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      );

      CREATE INDEX IF NOT EXISTS idx_interactions_subject ON adaptive_interactions(subject);
      CREATE INDEX IF NOT EXISTS idx_interactions_student ON adaptive_interactions(student_id);
      CREATE INDEX IF NOT EXISTS idx_feedback_interaction ON adaptive_feedback(interaction_id);
      CREATE INDEX IF NOT EXISTS idx_prompts_subject ON adaptive_prompts(subject);
      CREATE INDEX IF NOT EXISTS idx_weights_subject ON adaptive_weights(subject);
    `);
    
    console.log('✅ Database tables initialized successfully');
  } catch (error) {
    console.error('❌ Database initialization error:', error.message);
  }
}

app.listen(PORT, async () => {
  console.log(`\n🚀 Guide Adaptive Learning System running on port ${PORT}`);
  console.log(`📊 Analytics dashboard: http://localhost:${PORT}/api/analytics/dashboard`);
  console.log(`💚 Health check: http://localhost:${PORT}/health\n`);
  
  await initializeDatabase();
});

module.exports = app;
