const express = require('express');
const cors = require('cors');
const Stripe = require('stripe');
const { Pool } = require('pg');
require('dotenv').config();

const app = express();
const PORT = process.env.PAYMENTS_PORT || 3001;

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const db = new Pool({ connectionString: process.env.DATABASE_URL });

const REPLIT_DOMAIN = process.env.REPLIT_DOMAINS?.split(',')[0] || 'localhost:5000';
const BASE_URL = `https://${REPLIT_DOMAIN}`;
const PAYMENTS_API_SECRET = process.env.PAYMENTS_API_SECRET;

app.use(cors());

function requireApiAuth(req, res, next) {
  const authHeader = req.headers['x-api-secret'];
  
  if (!PAYMENTS_API_SECRET) {
    console.error('PAYMENTS_API_SECRET not configured');
    return res.status(500).json({ success: false, error: 'Server misconfigured' });
  }
  
  if (!authHeader || authHeader !== PAYMENTS_API_SECRET) {
    console.warn('Unauthorized API request from:', req.ip);
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  
  next();
}

app.post('/api/stripe/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  console.log(`Received Stripe event: ${event.type}`);

  try {
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(event.data.object);
        break;
      case 'customer.subscription.created':
      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object);
        break;
      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object);
        break;
      case 'invoice.payment_failed':
        await handlePaymentFailed(event.data.object);
        break;
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }
  } catch (err) {
    console.error(`Error handling ${event.type}:`, err);
  }

  res.json({ received: true });
});

app.use(express.json());

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'Guide Payments Service',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/products', async (req, res) => {
  try {
    const products = await stripe.products.list({ active: true });
    const prices = await stripe.prices.list({ active: true });
    
    const productsWithPrices = products.data.map(product => ({
      ...product,
      prices: prices.data.filter(price => price.product === product.id)
    }));
    
    res.json({ success: true, data: productsWithPrices });
  } catch (error) {
    console.error('Error fetching products:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/create-checkout-session', requireApiAuth, async (req, res) => {
  try {
    const { priceId, educatorId, email } = req.body;
    
    if (!priceId || !educatorId) {
      return res.status(400).json({ success: false, error: 'priceId and educatorId are required' });
    }

    const existingCustomer = await db.query(
      'SELECT stripe_customer_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    let customerId = existingCustomer.rows[0]?.stripe_customer_id;
    
    if (!customerId && email) {
      const customer = await stripe.customers.create({
        email,
        metadata: { educatorId: String(educatorId) }
      });
      customerId = customer.id;
      
      await db.query(
        'UPDATE users SET stripe_customer_id = $1 WHERE id = $2',
        [customerId, educatorId]
      );
    }

    const sessionParams = {
      mode: 'subscription',
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${BASE_URL}/?subscription=success`,
      cancel_url: `${BASE_URL}/?subscription=cancelled`,
      metadata: { educatorId: String(educatorId) }
    };

    if (customerId) {
      sessionParams.customer = customerId;
    } else if (email) {
      sessionParams.customer_email = email;
    }

    const session = await stripe.checkout.sessions.create(sessionParams);
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating checkout session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/create-portal-session', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.body;
    
    if (!educatorId) {
      return res.status(400).json({ success: false, error: 'educatorId is required' });
    }

    const result = await db.query(
      'SELECT stripe_customer_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    const customerId = result.rows[0]?.stripe_customer_id;
    
    if (!customerId) {
      return res.status(400).json({ success: false, error: 'No subscription found for this educator' });
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: `${BASE_URL}/`
    });
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating portal session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/subscription-status/:educatorId', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.params;
    
    const result = await db.query(
      `SELECT stripe_customer_id, stripe_subscription_id, subscription_status, 
              subscription_plan, trial_ends_at, subscription_ends_at 
       FROM users WHERE id = $1`,
      [educatorId]
    );
    
    if (!result.rows[0]) {
      return res.status(404).json({ success: false, error: 'Educator not found' });
    }
    
    const educator = result.rows[0];
    const isActive = ['active', 'trialing'].includes(educator.subscription_status);
    
    res.json({
      success: true,
      data: {
        isActive,
        status: educator.subscription_status || 'none',
        plan: educator.subscription_plan,
        trialEndsAt: educator.trial_ends_at,
        subscriptionEndsAt: educator.subscription_ends_at
      }
    });
  } catch (error) {
    console.error('Error checking subscription status:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

async function handleCheckoutCompleted(session) {
  console.log('Checkout completed:', session.id);
  
  const educatorId = session.metadata?.educatorId;
  const customerId = session.customer;
  const subscriptionId = session.subscription;
  
  if (educatorId && customerId) {
    await db.query(
      `UPDATE users SET 
        stripe_customer_id = $1,
        stripe_subscription_id = $2,
        subscription_status = 'active'
       WHERE id = $3`,
      [customerId, subscriptionId, educatorId]
    );
    console.log(`Updated educator ${educatorId} with subscription ${subscriptionId}`);
  }
}

async function handleSubscriptionUpdated(subscription) {
  console.log('Subscription updated:', subscription.id, 'Status:', subscription.status);
  
  const customerId = subscription.customer;
  const status = subscription.status;
  const plan = subscription.items?.data[0]?.price?.nickname || 
               (subscription.items?.data[0]?.price?.recurring?.interval === 'year' ? 'annual' : 'monthly');
  
  const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
  const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
  
  await db.query(
    `UPDATE users SET 
      stripe_subscription_id = $1,
      subscription_status = $2,
      subscription_plan = $3,
      trial_ends_at = $4,
      subscription_ends_at = $5
     WHERE stripe_customer_id = $6`,
    [subscription.id, status, plan, trialEnd, currentPeriodEnd, customerId]
  );
  console.log(`Updated subscription for customer ${customerId}`);
}

async function handleSubscriptionDeleted(subscription) {
  console.log('Subscription deleted:', subscription.id);
  
  const customerId = subscription.customer;
  
  await db.query(
    `UPDATE users SET 
      subscription_status = 'cancelled',
      subscription_ends_at = NOW()
     WHERE stripe_customer_id = $1`,
    [customerId]
  );
  console.log(`Cancelled subscription for customer ${customerId}`);
}

async function handlePaymentFailed(invoice) {
  console.log('Payment failed for invoice:', invoice.id);
  
  const customerId = invoice.customer;
  
  await db.query(
    `UPDATE users SET subscription_status = 'past_due' WHERE stripe_customer_id = $1`,
    [customerId]
  );
  console.log(`Marked subscription as past_due for customer ${customerId}`);
}

async function initDatabase() {
  try {
    await db.query(`
      ALTER TABLE users 
      ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
      ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
      ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'none',
      ADD COLUMN IF NOT EXISTS subscription_plan TEXT,
      ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP,
      ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMP
    `);
    console.log('Database columns initialized successfully');
  } catch (error) {
    console.error('Error initializing database columns:', error.message);
  }
}

async function startServer() {
  await initDatabase();
  
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`💳 Guide Payments Service running on port ${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`🔗 Webhook endpoint: ${BASE_URL}/api/stripe/webhook`);
  });
}

startServer();
