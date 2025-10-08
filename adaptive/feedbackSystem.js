class FeedbackSystem {
  constructor(db) {
    this.db = db;
    this.emojiMeanings = {
      '🤩': { sentiment: 'excellent', weight: 1.0, category: 'engagement' },
      '💡': { sentiment: 'insightful', weight: 0.9, category: 'understanding' },
      '🌟': { sentiment: 'loved_it', weight: 0.95, category: 'engagement' },
      '👍': { sentiment: 'helpful', weight: 0.7, category: 'utility' },
      '📚': { sentiment: 'curriculum_aligned', weight: 0.8, category: 'alignment' },
      '🌍': { sentiment: 'montessori_cosmic', weight: 0.85, category: 'philosophy' },
      '🤔': { sentiment: 'thinking', weight: 0.5, category: 'neutral' },
      '😕': { sentiment: 'confused', weight: 0.2, category: 'difficulty' },
      '❌': { sentiment: 'not_helpful', weight: 0.1, category: 'negative' }
    };
  }

  async logFeedback(interactionId, emoji) {
    const emojiData = this.emojiMeanings[emoji] || { 
      sentiment: 'unknown', 
      weight: 0.5, 
      category: 'neutral' 
    };
    
    await this.db.query(`
      INSERT INTO adaptive_feedback (
        interaction_id,
        emoji,
        sentiment,
        weight,
        category,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
    `, [
      interactionId,
      emoji,
      emojiData.sentiment,
      emojiData.weight,
      emojiData.category
    ]);
    
    return { logged: true, sentiment: emojiData.sentiment };
  }

  async analyzeFeedback(interactionId) {
    const interaction = await this.db.query(`
      SELECT subject, year_level, query_text, response_text
      FROM adaptive_interactions
      WHERE id = $1
    `, [interactionId]);
    
    const feedback = await this.db.query(`
      SELECT emoji, sentiment, weight, category
      FROM adaptive_feedback
      WHERE interaction_id = $1
    `, [interactionId]);
    
    if (feedback.rows.length === 0) {
      return { requiresAdjustment: false };
    }
    
    const interactionData = interaction.rows[0];
    const feedbackData = feedback.rows[0];
    
    const requiresAdjustment = feedbackData.weight < 0.4;
    
    const adjustmentVector = this.calculateAdjustmentVector(feedbackData);
    
    return {
      requiresAdjustment,
      subject: interactionData.subject,
      feedbackPattern: feedbackData,
      adjustmentVector,
      sentiment: feedbackData.sentiment
    };
  }

  calculateAdjustmentVector(feedbackData) {
    const vector = {
      montessoriWeight: 0,
      curriculumWeight: 0,
      scaffoldingWeight: 0,
      complexityLevel: 0
    };
    
    switch (feedbackData.category) {
      case 'difficulty':
        vector.scaffoldingWeight = 0.15;
        vector.complexityLevel = -0.1;
        break;
      
      case 'philosophy':
        vector.montessoriWeight = feedbackData.weight > 0.7 ? 0.1 : -0.1;
        break;
      
      case 'alignment':
        vector.curriculumWeight = feedbackData.weight > 0.7 ? 0.1 : -0.1;
        break;
      
      case 'engagement':
        if (feedbackData.weight < 0.4) {
          vector.scaffoldingWeight = 0.1;
          vector.complexityLevel = -0.05;
        }
        break;
      
      case 'negative':
        vector.scaffoldingWeight = 0.2;
        vector.complexityLevel = -0.15;
        break;
    }
    
    return vector;
  }

  async getAverageFeedback(subject = null, timeframe = '7 days') {
    const whereClause = subject 
      ? 'WHERE subject = $1 AND af.created_at > NOW() - $2::interval'
      : 'WHERE af.created_at > NOW() - $1::interval';
    
    const params = subject ? [subject, timeframe] : [timeframe];
    
    const result = await this.db.query(`
      SELECT 
        AVG(af.weight) as avg_weight,
        COUNT(*) as total_feedback,
        COUNT(CASE WHEN af.weight >= 0.7 THEN 1 END) as positive,
        COUNT(CASE WHEN af.weight < 0.4 THEN 1 END) as negative,
        array_agg(DISTINCT af.emoji) as emoji_distribution
      FROM adaptive_feedback af
      JOIN adaptive_interactions ai ON af.interaction_id = ai.id
      ${whereClause}
    `, params);
    
    const data = result.rows[0];
    
    return {
      averageWeight: parseFloat(data.avg_weight) || 0.5,
      totalFeedback: parseInt(data.total_feedback) || 0,
      positiveCount: parseInt(data.positive) || 0,
      negativeCount: parseInt(data.negative) || 0,
      emojiDistribution: data.emoji_distribution || []
    };
  }

  async getFeedbackTrends(subject, days = 7) {
    const result = await this.db.query(`
      SELECT 
        DATE(af.created_at) as date,
        AVG(af.weight) as avg_weight,
        COUNT(*) as count,
        array_agg(af.emoji) as emojis
      FROM adaptive_feedback af
      JOIN adaptive_interactions ai ON af.interaction_id = ai.id
      WHERE ai.subject = $1
        AND af.created_at > NOW() - interval '${days} days'
      GROUP BY DATE(af.created_at)
      ORDER BY date ASC
    `, [subject]);
    
    return result.rows;
  }

  async getEmojiStats(timeframe = '7 days') {
    const result = await this.db.query(`
      SELECT 
        emoji,
        COUNT(*) as count,
        sentiment,
        category,
        AVG(weight) as avg_weight
      FROM adaptive_feedback
      WHERE created_at > NOW() - $1::interval
      GROUP BY emoji, sentiment, category
      ORDER BY count DESC
    `, [timeframe]);
    
    return result.rows;
  }

  async getStudentFeedbackProfile(studentId) {
    const result = await this.db.query(`
      SELECT 
        ai.subject,
        COUNT(*) as interactions,
        AVG(af.weight) as avg_satisfaction,
        array_agg(DISTINCT af.emoji) as preferred_emojis,
        COUNT(CASE WHEN af.category = 'difficulty' THEN 1 END) as confusion_count
      FROM adaptive_feedback af
      JOIN adaptive_interactions ai ON af.interaction_id = ai.id
      WHERE ai.student_id = $1
      GROUP BY ai.subject
    `, [studentId]);
    
    return result.rows;
  }
}

module.exports = FeedbackSystem;
