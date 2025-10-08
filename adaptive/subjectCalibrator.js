class SubjectCalibrator {
  constructor(db, trendingKeywords = null) {
    this.db = db;
    this.trendingKeywords = trendingKeywords;
    this.defaultWeights = {
      montessoriWeight: 0.7,
      curriculumWeight: 0.6,
      scaffoldingWeight: 0.5,
      complexityLevel: 0.6
    };
  }

  async getSubjectWeights(subject, useTrendingBoost = false) {
    const result = await this.db.query(`
      SELECT 
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        updated_at
      FROM adaptive_weights
      WHERE subject = $1
      ORDER BY updated_at DESC
      LIMIT 1
    `, [subject]);
    
    if (result.rows.length === 0) {
      await this.initializeWeights(subject);
      return this.defaultWeights;
    }
    
    const weights = result.rows[0];
    const baseWeights = {
      montessoriWeight: parseFloat(weights.montessori_weight),
      curriculumWeight: parseFloat(weights.curriculum_weight),
      scaffoldingWeight: parseFloat(weights.scaffolding_weight),
      complexityLevel: parseFloat(weights.complexity_level)
    };

    if (useTrendingBoost && this.trendingKeywords) {
      const trendingWeight = await this.trendingKeywords.getSubjectWeight(subject);
      return {
        ...baseWeights,
        trendingBoost: trendingWeight,
        effectiveCurriculumWeight: this.clamp(
          baseWeights.curriculumWeight * trendingWeight,
          0.3, 1.0
        )
      };
    }
    
    return baseWeights;
  }

  async initializeWeights(subject) {
    await this.db.query(`
      INSERT INTO adaptive_weights (
        subject,
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        created_at,
        updated_at
      ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    `, [
      subject,
      this.defaultWeights.montessoriWeight,
      this.defaultWeights.curriculumWeight,
      this.defaultWeights.scaffoldingWeight,
      this.defaultWeights.complexityLevel
    ]);
  }

  async adjustWeights(subject, adjustmentVector) {
    const currentWeights = await this.getSubjectWeights(subject);
    
    const newWeights = {
      montessoriWeight: this.clamp(
        currentWeights.montessoriWeight + adjustmentVector.montessoriWeight,
        0.3, 1.0
      ),
      curriculumWeight: this.clamp(
        currentWeights.curriculumWeight + adjustmentVector.curriculumWeight,
        0.3, 1.0
      ),
      scaffoldingWeight: this.clamp(
        currentWeights.scaffoldingWeight + adjustmentVector.scaffoldingWeight,
        0.2, 1.0
      ),
      complexityLevel: this.clamp(
        currentWeights.complexityLevel + adjustmentVector.complexityLevel,
        0.2, 1.0
      )
    };
    
    await this.db.query(`
      INSERT INTO adaptive_weights (
        subject,
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        created_at,
        updated_at
      ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    `, [
      subject,
      newWeights.montessoriWeight,
      newWeights.curriculumWeight,
      newWeights.scaffoldingWeight,
      newWeights.complexityLevel
    ]);
    
    return newWeights;
  }

  clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  async getWeightHistory(subject, days = 30) {
    const result = await this.db.query(`
      SELECT 
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        updated_at
      FROM adaptive_weights
      WHERE subject = $1
        AND updated_at > NOW() - interval '${days} days'
      ORDER BY updated_at ASC
    `, [subject]);
    
    return result.rows.map(row => ({
      montessoriWeight: parseFloat(row.montessori_weight),
      curriculumWeight: parseFloat(row.curriculum_weight),
      scaffoldingWeight: parseFloat(row.scaffolding_weight),
      complexityLevel: parseFloat(row.complexity_level),
      timestamp: row.updated_at
    }));
  }

  async getOptimalWeightsForStudent(studentId) {
    const result = await this.db.query(`
      SELECT 
        ai.subject,
        AVG(CASE 
          WHEN af.category = 'philosophy' AND af.weight > 0.7 THEN 0.8
          ELSE aw.montessori_weight 
        END) as optimal_montessori,
        AVG(CASE 
          WHEN af.category = 'alignment' AND af.weight > 0.7 THEN 0.8
          ELSE aw.curriculum_weight 
        END) as optimal_curriculum,
        AVG(CASE 
          WHEN af.category = 'difficulty' THEN aw.scaffolding_weight + 0.2
          ELSE aw.scaffolding_weight 
        END) as optimal_scaffolding
      FROM adaptive_interactions ai
      JOIN adaptive_feedback af ON af.interaction_id = ai.id
      JOIN adaptive_weights aw ON aw.subject = ai.subject
      WHERE ai.student_id = $1
        AND ai.created_at > NOW() - interval '14 days'
      GROUP BY ai.subject
    `, [studentId]);
    
    return result.rows;
  }

  async compareSubjects() {
    const result = await this.db.query(`
      SELECT DISTINCT ON (subject)
        subject,
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        (
          SELECT AVG(weight)
          FROM adaptive_feedback af
          JOIN adaptive_interactions ai ON af.interaction_id = ai.id
          WHERE ai.subject = adaptive_weights.subject
            AND af.created_at > NOW() - interval '7 days'
        ) as avg_feedback
      FROM adaptive_weights
      ORDER BY subject, updated_at DESC
    `);
    
    return result.rows;
  }

  async resetWeights(subject) {
    await this.db.query(`
      INSERT INTO adaptive_weights (
        subject,
        montessori_weight,
        curriculum_weight,
        scaffolding_weight,
        complexity_level,
        created_at,
        updated_at
      ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    `, [
      subject,
      this.defaultWeights.montessoriWeight,
      this.defaultWeights.curriculumWeight,
      this.defaultWeights.scaffoldingWeight,
      this.defaultWeights.complexityLevel
    ]);
    
    return this.defaultWeights;
  }
}

module.exports = SubjectCalibrator;
