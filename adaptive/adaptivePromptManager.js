class AdaptivePromptManager {
  constructor(db, openai) {
    this.db = db;
    this.openai = openai;
    this.basePrompts = this.initializeBasePrompts();
  }

  initializeBasePrompts() {
    return {
      default: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, a Montessori-inspired AI companion helping students explore cosmic education. 
Emphasize interconnections, wonder, and the child's place in the universe.`,
      
      geography: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, helping students explore geography through Montessori cosmic education.
Connect geographical concepts to the whole Earth story and human interconnectedness.`,
      
      history: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, helping students discover history as part of the cosmic timeline.
Show how past events connect to present and future, emphasizing human contribution to civilization.`,
      
      science: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, revealing scientific concepts through cosmic education principles.
Connect science to the grand narrative of the universe and life's evolution.`,
      
      mathematics: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, exploring mathematics as the language of the cosmos.
Show mathematical patterns in nature and their role in understanding our universe.`
    };
  }

  async getAdaptivePrompt(subject = 'default', yearLevel = 'Year 7') {
    const basePrompt = this.basePrompts[subject.toLowerCase()] || this.basePrompts.default;
    
    const recentFeedback = await this.getRecentFeedback(subject);
    
    if (recentFeedback.needsUpdate) {
      return await this.generateUpdatedPrompt(basePrompt, subject, recentFeedback);
    }
    
    const savedPrompt = await this.getSavedPrompt(subject);
    return savedPrompt || basePrompt;
  }

  async generateUpdatedPrompt(basePrompt, subject, feedback) {
    const updateInstructions = this.buildUpdateInstructions(feedback);
    
    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { 
          role: 'system', 
          content: `IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all prompts you generate.

You are a prompt engineer. Update the following system prompt based on user feedback patterns.
Maintain Montessori philosophy while addressing the feedback. Ensure the updated prompt includes British English instructions.` 
        },
        { 
          role: 'user', 
          content: `Base prompt: ${basePrompt}\n\nFeedback patterns: ${updateInstructions}\n\nGenerate an improved prompt.` 
        }
      ],
      temperature: 0.3,
      max_tokens: 500
    });
    
    const updatedPrompt = response.choices[0].message.content;
    
    await this.savePrompt(subject, updatedPrompt);
    
    return updatedPrompt;
  }

  buildUpdateInstructions(feedback) {
    const instructions = [];
    
    if (feedback.tooComplex > 0.5) {
      instructions.push('Simplify language and concepts');
    }
    
    if (feedback.needsMoreExamples > 0.6) {
      instructions.push('Include more concrete examples');
    }
    
    if (feedback.tooAbstract > 0.5) {
      instructions.push('Add more practical connections');
    }
    
    if (feedback.lovesCurriculum > 0.7) {
      instructions.push('Strengthen Australian Curriculum V9 references');
    }
    
    if (feedback.lovesMontessori > 0.7) {
      instructions.push('Deepen Montessori cosmic education elements');
    }
    
    return instructions.join('; ');
  }

  async getRecentFeedback(subject) {
    const result = await this.db.query(`
      SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN af.emoji = '😕' THEN 1 ELSE 0 END) as confused,
        SUM(CASE WHEN af.emoji = '🤩' THEN 1 ELSE 0 END) as loved,
        SUM(CASE WHEN af.emoji = '📚' THEN 1 ELSE 0 END) as curriculum_focused,
        SUM(CASE WHEN af.emoji = '🌍' THEN 1 ELSE 0 END) as montessori_focused
      FROM adaptive_feedback af
      JOIN adaptive_interactions ai ON af.interaction_id = ai.id
      WHERE ai.subject = $1 
        AND af.created_at > NOW() - interval '24 hours'
    `, [subject]);
    
    const data = result.rows[0];
    const total = parseInt(data.total);
    
    if (total < 10) {
      return { needsUpdate: false };
    }
    
    return {
      needsUpdate: total >= 10,
      tooComplex: parseInt(data.confused) / total,
      lovesCurriculum: parseInt(data.curriculum_focused) / total,
      lovesMontessori: parseInt(data.montessori_focused) / total,
      needsMoreExamples: parseInt(data.confused) / total
    };
  }

  async savePrompt(subject, prompt) {
    await this.db.query(`
      INSERT INTO adaptive_prompts (subject, prompt_text, version, created_at)
      VALUES ($1::varchar, $2::text, (
        SELECT COALESCE(MAX(version), 0) + 1 
        FROM adaptive_prompts 
        WHERE subject = $1::varchar
      ), NOW())
    `, [subject, prompt]);
  }

  async getSavedPrompt(subject) {
    const result = await this.db.query(`
      SELECT prompt_text 
      FROM adaptive_prompts 
      WHERE subject = $1 
      ORDER BY version DESC 
      LIMIT 1
    `, [subject]);
    
    return result.rows[0]?.prompt_text;
  }

  async getCurrentVersion(subject) {
    const result = await this.db.query(`
      SELECT version 
      FROM adaptive_prompts 
      WHERE subject = $1 
      ORDER BY version DESC 
      LIMIT 1
    `, [subject]);
    
    return result.rows[0]?.version || 1;
  }

  async updatePromptFromFeedback(subject, feedbackPattern) {
    const currentPrompt = await this.getSavedPrompt(subject) || this.basePrompts[subject];
    return await this.generateUpdatedPrompt(currentPrompt, subject, feedbackPattern);
  }

  async refreshSystemPromptWithHelpfulness() {
    const result = await this.db.query(`
      SELECT 
        ai.subject,
        COUNT(*) as total,
        SUM(CASE WHEN af.weight >= 0.6 THEN 1 ELSE 0 END) as helpful_count
      FROM adaptive_feedback af
      JOIN adaptive_interactions ai ON af.interaction_id = ai.id
      WHERE ai.subject IS NOT NULL 
        AND af.created_at > NOW() - interval '7 days'
      GROUP BY ai.subject
      HAVING COUNT(*) >= 5
    `);

    const stats = {};
    for (const row of result.rows) {
      const helpfulRatio = parseFloat(row.helpful_count) / parseFloat(row.total);
      stats[row.subject] = {
        helpful: parseFloat(row.helpful_count),
        total: parseFloat(row.total),
        ratio: helpfulRatio
      };
    }

    let focus = "";
    for (const [subject, { ratio }] of Object.entries(stats)) {
      if (ratio < 0.5) {
        focus += `Refine ${subject} to offer more ethical ambiguity and abstract challenges.\n`;
      }
    }

    const prompt = `You are Montessori GuideChat. You begin provocations with a quote or visual idea, followed by an open ethical or societal challenge.
Improvement focus:
${focus || "Maintain current sophistication."}`.trim();

    await this.db.query(`
      INSERT INTO system_config (config_key, config_value, updated_at)
      VALUES ('systemPrompt_dynamic', $1, NOW())
      ON CONFLICT (config_key) 
      DO UPDATE SET config_value = $1, updated_at = NOW()
    `, [prompt]);

    await this.db.query(`
      INSERT INTO system_config (config_key, config_value, updated_at)
      VALUES ('lastPromptRefresh', $1, NOW())
      ON CONFLICT (config_key) 
      DO UPDATE SET config_value = $1, updated_at = NOW()
    `, [new Date().toISOString()]);

    return { prompt, stats };
  }

  async getDynamicSystemPrompt() {
    const result = await this.db.query(`
      SELECT config_value 
      FROM system_config 
      WHERE config_key = 'systemPrompt_dynamic'
    `);
    
    return result.rows[0]?.config_value || this.basePrompts.default;
  }
}

module.exports = AdaptivePromptManager;
