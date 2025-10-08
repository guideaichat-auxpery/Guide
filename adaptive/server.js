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
    
    const { db } = adaptiveCore;
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
      ) VALUES ($1, $2, $3, $4, 'rating', NOW())
    `, [
      interactionId,
      emoji,
      `rating_${rating}`,
      rating / 5.0
    ]);
    
    res.json({ success: true, rating });
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
    const { input, subject, studentId } = req.body;
    
    if (!input || !subject) {
      return res.status(400).json({
        success: false,
        error: 'input and subject required'
      });
    }
    
    await adaptiveCore.semanticLogger.logInteraction({
      query: input,
      response: '',
      subject,
      yearLevel: 'Year 7',
      studentId: studentId || 'anonymous'
    });
    
    const weight = await adaptiveCore.subjectCalibrator.getSubjectWeights(subject);
    const dynamicPrompt = await adaptiveCore.promptManager.getAdaptivePrompt(subject);
    
    res.json({ 
      systemPrompt: dynamicPrompt, 
      weight 
    });
  } catch (error) {
    console.error('Message pipeline error:', error);
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

      CREATE TABLE IF NOT EXISTS system_config (
        id SERIAL PRIMARY KEY,
        config_key VARCHAR(100) UNIQUE NOT NULL,
        config_value TEXT,
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

async function runAutoRefreshCycle() {
  const { db } = adaptiveCore;
  
  try {
    const result = await db.query(`
      SELECT config_value, updated_at 
      FROM system_config 
      WHERE config_key = 'lastPromptRefresh'
    `);
    
    const now = Date.now();
    const lastRun = result.rows[0]?.updated_at;
    const REFRESH_INTERVAL = 72 * 60 * 60 * 1000;
    
    if (!lastRun || now - new Date(lastRun).getTime() > REFRESH_INTERVAL) {
      console.log('🔄 Running 72-hour auto-refresh cycle...');
      
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
      
      await db.query(`
        INSERT INTO system_config (config_key, config_value, updated_at)
        VALUES ('lastPromptRefresh', $1, NOW())
        ON CONFLICT (config_key) 
        DO UPDATE SET config_value = $1, updated_at = NOW()
      `, [new Date().toISOString()]);
      
      console.log('✅ Auto-refresh cycle completed');
    } else {
      const hoursRemaining = Math.ceil((REFRESH_INTERVAL - (now - new Date(lastRun).getTime())) / (60 * 60 * 1000));
      console.log(`⏰ Next auto-refresh in ~${hoursRemaining} hours`);
    }
  } catch (error) {
    console.error('❌ Auto-refresh cycle error:', error.message);
  }
}

app.listen(PORT, async () => {
  console.log(`\n🚀 Guide Adaptive Learning System running on port ${PORT}`);
  console.log(`📊 Analytics dashboard: http://localhost:${PORT}/api/analytics/dashboard`);
  console.log(`💚 Health check: http://localhost:${PORT}/health\n`);
  
  await initializeDatabase();
  await runAutoRefreshCycle();
  
  setInterval(runAutoRefreshCycle, 60 * 60 * 1000);
});

module.exports = app;
