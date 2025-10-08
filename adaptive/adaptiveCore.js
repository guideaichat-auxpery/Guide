const OpenAI = require('openai');
const { Pool } = require('pg');
require('dotenv').config();

const PromptManager = require('./adaptivePromptManager');
const SemanticLogger = require('./semanticLogger');
const FeedbackSystem = require('./feedbackSystem');
const SubjectCalibrator = require('./subjectCalibrator');
const TrendingKeywords = require('./trendingKeywords');

class AdaptiveCore {
  constructor() {
    this.openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });
    
    this.db = new Pool({
      connectionString: process.env.DATABASE_URL
    });
    
    this.promptManager = new PromptManager(this.db, this.openai);
    this.semanticLogger = new SemanticLogger(this.db, this.openai);
    this.feedbackSystem = new FeedbackSystem(this.db);
    this.subjectCalibrator = new SubjectCalibrator(this.db);
    this.trendingKeywords = new TrendingKeywords(this.db);
  }

  async generateResponse(userQuery, context = {}) {
    const { studentId, subject, yearLevel } = context;
    
    const systemPrompt = await this.promptManager.getAdaptivePrompt(subject, yearLevel);
    
    const weights = await this.subjectCalibrator.getSubjectWeights(subject);
    
    const enhancedPrompt = this.applyWeights(systemPrompt, weights);
    
    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: enhancedPrompt },
        { role: 'user', content: userQuery }
      ],
      temperature: 0.7,
      max_tokens: 1000
    });
    
    const answer = response.choices[0].message.content;
    
    await this.semanticLogger.logInteraction({
      query: userQuery,
      response: answer,
      subject,
      yearLevel,
      studentId
    });
    
    return {
      answer,
      interactionId: await this.getLastInteractionId()
    };
  }

  applyWeights(prompt, weights) {
    let enhanced = prompt;
    
    if (weights.montessoriWeight > 0.7) {
      enhanced += "\n\nEmphasize Montessori cosmic education principles strongly.";
    }
    
    if (weights.curriculumWeight > 0.7) {
      enhanced += "\n\nPrioritize Australian Curriculum V9 alignment in your response.";
    }
    
    if (weights.scaffoldingWeight > 0.8) {
      enhanced += "\n\nProvide extensive scaffolding and step-by-step guidance.";
    }
    
    return enhanced;
  }

  async recordFeedback(interactionId, emoji) {
    await this.feedbackSystem.logFeedback(interactionId, emoji);
    
    const feedback = await this.feedbackSystem.analyzeFeedback(interactionId);
    
    if (feedback.requiresAdjustment) {
      await this.subjectCalibrator.adjustWeights(
        feedback.subject,
        feedback.adjustmentVector
      );
      
      await this.promptManager.updatePromptFromFeedback(
        feedback.subject,
        feedback.feedbackPattern
      );
    }
  }

  async getLastInteractionId() {
    const result = await this.db.query(
      'SELECT id FROM adaptive_interactions ORDER BY created_at DESC LIMIT 1'
    );
    return result.rows[0]?.id;
  }

  async getAnalytics(subject = null, timeframe = '7 days') {
    const stats = {
      totalInteractions: await this.getTotalInteractions(subject, timeframe),
      averageFeedback: await this.feedbackSystem.getAverageFeedback(subject, timeframe),
      topTopics: await this.semanticLogger.getTopTopics(subject, timeframe),
      currentWeights: await this.subjectCalibrator.getSubjectWeights(subject),
      promptVersion: await this.promptManager.getCurrentVersion(subject)
    };
    
    return stats;
  }

  async getTotalInteractions(subject, timeframe) {
    const query = subject 
      ? 'SELECT COUNT(*) FROM adaptive_interactions WHERE subject = $1 AND created_at > NOW() - $2::interval'
      : 'SELECT COUNT(*) FROM adaptive_interactions WHERE created_at > NOW() - $1::interval';
    
    const params = subject ? [subject, timeframe] : [timeframe];
    const result = await this.db.query(query, params);
    
    return parseInt(result.rows[0].count);
  }
}

module.exports = AdaptiveCore;
