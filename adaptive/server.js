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

app.get('/api/weights', async (req, res) => {
  try {
    const weights = await adaptiveCore.subjectCalibrator.getSubjectWeights();
    
    res.json({ 
      success: true, 
      subject: 'default',
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

app.get('/api/weights/:subject', async (req, res) => {
  try {
    const { subject } = req.params;
    const weights = await adaptiveCore.subjectCalibrator.getSubjectWeights(subject);
    
    res.json({ 
      success: true, 
      subject,
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

// === PROFESSIONAL DEVELOPMENT EXPERT MODE ===
app.post("/api/pd-expert", async (req, res) => {
  try {
    console.log('🧭 PD Expert request received:', { userEmail: req.body.userEmail, promptLength: req.body.prompt?.length });
    
    const { userEmail, prompt } = req.body;

    // Restrict to authorized email only
    if (userEmail !== "guideaichat@gmail.com") {
      console.log('❌ Access denied for:', userEmail);
      return res.status(403).json({
        success: false,
        error: "Access denied. This function is restricted to the authorized account.",
      });
    }
    
    console.log('✅ Access granted, processing request...');

    const uiLabel = "🧭 PD Mode";

    // Self-learning memory logic - retrieve recent prompts
    let previousPrompts = [];
    try {
      const { value: allKeys } = await kvDatabase.list();
      const pdKeys = allKeys.filter(k => k.startsWith("pdprompts:"));
      
      for (const key of pdKeys) {
        const record = await kvDatabase.get(key);
        if (record?.userEmail === userEmail) {
          previousPrompts.push(record.prompt);
        }
      }
    } catch (err) {
      console.warn("KV retrieval for PD prompts:", err);
    }

    // Keep memory manageable (last 15 prompts)
    if (previousPrompts.length > 15) {
      previousPrompts = previousPrompts.slice(-15);
    }

    // Summarize user's prior focus
    let memorySummary = "";
    if (previousPrompts.length > 0) {
      const summaryResponse = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
          {
            role: "system",
            content: "You are summarizing key learning patterns and developmental focus areas from previous professional development prompts. Be concise and thematic.",
          },
          {
            role: "user",
            content: previousPrompts.join("\n\n"),
          },
        ],
        temperature: 0.3,
      });
      memorySummary = summaryResponse.choices[0].message.content;
    }

    // Store current prompt for continued self-learning
    await kvDatabase.set(`pdprompts:${Date.now()}`, { userEmail, prompt });

    // Contextual keyword analysis
    const keywordContexts = {
      "adult learning": "Integrate andragogy principles—autonomy, experience-based learning, relevance, reflection.",
      "instructional coaching": "Apply evidence-based coaching models with reflective dialogue and goal setting.",
      "course design": "Ensure alignment between evidence base, learning goals, and pedagogical coherence.",
      "montessori": "Anchor in Montessori principles—Prepared Adult, intrinsic motivation, observation, holistic development.",
      "workshop": "Emphasize experiential, interactive learning that honors participants' prior experience.",
      "evidence base": "Draw upon credible, peer-reviewed sources demonstrating improved student outcomes.",
    };

    let matchedContexts = Object.entries(keywordContexts)
      .filter(([key]) => prompt.toLowerCase().includes(key))
      .map(([_, context]) => context)
      .join(" ");

    if (!matchedContexts) {
      matchedContexts = "Default to evidence-based, adult-learning-oriented, Montessori-consistent professional development guidance.";
    }

    // System prompt for PD Expert role - ENHANCED FOR COMPREHENSIVE DETAIL
    const systemPrompt = `
You are a Professional Development Expert with 25–50 years of experience as an instructional coach, PD trainer, and facilitator.
You specialize in Montessori education and adult learning.

CRITICAL: Provide COMPREHENSIVE, DETAILED, IN-DEPTH responses. This is professional development coaching - depth and thoroughness are essential.

Your role:
- Provide evidence-based, experience-grounded professional development advice with extensive detail
- Model coherence between learning goals, pedagogy, and content with specific examples
- Reference reputable frameworks with detailed explanations:
  • Harvard's Instructional Moves (https://instructionalmoves.gse.harvard.edu/professional-development-facilitation-guide)
  • Edutopia's PD facilitation strategies
  • Adult learning theory (Knowles' andragogy, Kolb's experiential learning cycle)
  • Wenger's Communities of Practice
  • Schön's Reflective Practice
  • Joyce & Showers' Coaching Models
  • Global Partnership for Education on teacher training improvement
- Encourage reflective and self-directed learning among educators with specific prompts
- Maintain a Montessori-informed tone—calm, curious, observant, and empowering
- Use Australian educational context and terminology when relevant
- Provide multiple practical examples for each concept
- Include specific activities, timelines, and implementation steps
- Address potential challenges and how to overcome them
- Offer variations for different contexts (school size, experience levels, etc.)

REQUIRED STRUCTURE (Use all sections with extensive detail):

1️⃣ **COMPREHENSIVE SUMMARY** (2-3 paragraphs)
   - Reframe the question to show deep understanding
   - Identify underlying needs and goals
   - Connect to broader PD principles

2️⃣ **EVIDENCE-BASED INSIGHTS & FRAMEWORKS** (3-5 paragraphs)
   - Cite specific research and frameworks with explanations
   - Provide context from adult learning theory
   - Include relevant statistics or findings where applicable
   - Explain WHY these frameworks matter for this specific situation
   - Draw connections between multiple frameworks

3️⃣ **DETAILED APPROACH & STRUCTURE** (4-6 paragraphs with bullet points)
   - Step-by-step implementation guide
   - Specific activities with timing (e.g., "15-minute paired reflection")
   - Materials needed and preparation required
   - Sample scripts or facilitation language
   - Multiple variations for different contexts
   - Anticipated challenges and solutions
   - Assessment and feedback mechanisms

4️⃣ **MONTESSORI CONNECTIONS** (2-3 paragraphs)
   - Deep dive into Montessori philosophy relevance
   - Specific quotes from Montessori texts where applicable
   - How Prepared Adult principles apply
   - Connection to cosmic education or other Montessori concepts
   - Practical ways to honor Montessori values in this PD context

5️⃣ **IMPLEMENTATION TIMELINE & NEXT STEPS** (detailed action plan)
   - Immediate next steps (today/this week)
   - Short-term actions (1-4 weeks)
   - Medium-term development (1-3 months)
   - Long-term sustainability strategies
   - Specific reflective prompts for ongoing learning
   - Resources for continued exploration (books, articles, websites)
   - Metrics for measuring success

6️⃣ **PRACTICAL EXAMPLES & SCENARIOS** (2-3 detailed examples)
   - Real-world applications
   - Sample dialogue or facilitator moves
   - What it looks like in practice
   - Variations for different settings

**TONE & STYLE:**
- Write as a wise, experienced mentor sharing hard-won insights
- Balance theoretical grounding with practical, actionable advice
- Use storytelling and concrete examples liberally
- Acknowledge complexity while providing clarity
- Encourage experimentation and reflection
- Be warm, supportive, and empowering

**LENGTH EXPECTATION:** Aim for 800-1500 words minimum. Comprehensive detail is valued over brevity.
`;

    // Generate expert response with extended token limit for comprehensive detail
    console.log('🤖 Calling OpenAI API with max_tokens: 6000...');
    
    // Add timeout wrapper
    const apiCallPromise = openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: systemPrompt },
        {
          role: "assistant",
          content: `Prior user focus summary (memory): ${memorySummary || "No prior history yet."}`,
        },
        {
          role: "user",
          content: `Prompt: ${prompt}\nContext cues: ${matchedContexts}`,
        },
      ],
      temperature: 0.7,
      max_tokens: 6000, // Reduced for better performance
    });
    
    // 90 second timeout for OpenAI API
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('OpenAI API timeout after 90 seconds')), 90000)
    );
    
    const response = await Promise.race([apiCallPromise, timeoutPromise]);

    console.log('✅ OpenAI API response received');
    const output = response.choices[0].message.content;
    console.log(`📝 Response length: ${output.length} characters`);

    res.json({
      success: true,
      role: "PD Expert",
      label: uiLabel,
      output,
    });
  } catch (error) {
    console.error('PD Expert error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

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
