const express = require('express');

function createAnalyticsRouter(adaptiveCore) {
  const router = express.Router();
  
  router.get('/analytics/overview', async (req, res) => {
    try {
      const { subject, timeframe = '7 days' } = req.query;
      
      const analytics = await adaptiveCore.getAnalytics(subject, timeframe);
      
      res.json({
        success: true,
        data: analytics,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/feedback-trends', async (req, res) => {
    try {
      const { subject, days = 7 } = req.query;
      
      if (!subject) {
        return res.status(400).json({
          success: false,
          error: 'Subject parameter required'
        });
      }
      
      const trends = await adaptiveCore.feedbackSystem.getFeedbackTrends(subject, parseInt(days));
      
      res.json({
        success: true,
        subject,
        trends,
        period: `${days} days`
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/weight-history', async (req, res) => {
    try {
      const { subject, days = 30 } = req.query;
      
      if (!subject) {
        return res.status(400).json({
          success: false,
          error: 'Subject parameter required'
        });
      }
      
      const history = await adaptiveCore.subjectCalibrator.getWeightHistory(subject, parseInt(days));
      
      res.json({
        success: true,
        subject,
        history,
        period: `${days} days`
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/emoji-stats', async (req, res) => {
    try {
      const { timeframe = '7 days' } = req.query;
      
      const stats = await adaptiveCore.feedbackSystem.getEmojiStats(timeframe);
      
      res.json({
        success: true,
        emojiStats: stats,
        timeframe
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/subject-comparison', async (req, res) => {
    try {
      const comparison = await adaptiveCore.subjectCalibrator.compareSubjects();
      
      res.json({
        success: true,
        subjects: comparison
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/student-profile/:studentId', async (req, res) => {
    try {
      const { studentId } = req.params;
      
      const profile = await adaptiveCore.feedbackSystem.getStudentFeedbackProfile(studentId);
      const optimalWeights = await adaptiveCore.subjectCalibrator.getOptimalWeightsForStudent(studentId);
      
      res.json({
        success: true,
        studentId,
        profile,
        optimalWeights
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/topics', async (req, res) => {
    try {
      const { subject, timeframe = '7 days' } = req.query;
      
      const topics = await adaptiveCore.semanticLogger.getTopTopics(subject, timeframe);
      
      res.json({
        success: true,
        topics,
        subject: subject || 'all',
        timeframe
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/clusters/:subject', async (req, res) => {
    try {
      const { subject } = req.params;
      const { days = 7 } = req.query;
      
      const clusters = await adaptiveCore.semanticLogger.clusterInteractions(subject, parseInt(days));
      
      res.json({
        success: true,
        subject,
        clusters,
        period: `${days} days`
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.post('/analytics/feedback', async (req, res) => {
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
        message: 'Feedback recorded and system adjusted'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.post('/analytics/reset-weights', async (req, res) => {
    try {
      const { subject } = req.body;
      
      if (!subject) {
        return res.status(400).json({
          success: false,
          error: 'Subject parameter required'
        });
      }
      
      const newWeights = await adaptiveCore.subjectCalibrator.resetWeights(subject);
      
      res.json({
        success: true,
        message: `Weights reset for ${subject}`,
        weights: newWeights
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  router.get('/analytics/dashboard', async (req, res) => {
    try {
      const subjects = ['Geography', 'History', 'Science', 'Mathematics'];
      const dashboardData = {};
      
      for (const subject of subjects) {
        dashboardData[subject] = {
          analytics: await adaptiveCore.getAnalytics(subject, '7 days'),
          weights: await adaptiveCore.subjectCalibrator.getSubjectWeights(subject),
          feedbackAvg: await adaptiveCore.feedbackSystem.getAverageFeedback(subject, '7 days')
        };
      }
      
      res.json({
        success: true,
        dashboard: dashboardData,
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  return router;
}

module.exports = createAnalyticsRouter;
